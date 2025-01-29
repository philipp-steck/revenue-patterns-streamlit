import re
import time
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from dateutil.parser import parse
from pandas.api.types import (
    is_any_real_numeric_dtype,
    is_bool_dtype,
    is_datetime64_any_dtype,
)


@st.cache_data
def load_data(uploaded_file):
    """Load data from a CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


def convert_timestamps(df, column):
    if is_datetime64_any_dtype(df[column]):
        return df[column]
    else:
        if is_any_real_numeric_dtype(df[column]):
            column = df[column].apply(lambda x: datetime.fromtimestamp(x))
        else:
            column = df[column].apply(lambda x: parse(x))
        return column


@st.cache_data
def preprocess_data(df):
    """Preprocess the data for analysis."""

    df["timestamp"] = convert_timestamps(df, "timestamp")

    # Check if is_activation is a boolean or timestamp
    if "is_activation" not in df.columns:
        df = df.rename(
            columns={"first_touchpoint": "is_activation"}
        )  # current test file column is called first touchpoint

    if is_bool_dtype(df["is_activation"]) or df["is_activation"].isin([0, 1]).all():
        first_touchpoint = (
            df.loc[df.is_activation]
            .groupby("user_id")["timestamp"]
            .min()
            .reset_index()
            .rename(columns={"timestamp": "first_touchpoint"})
            .copy()
        )

        df = df.merge(first_touchpoint, on="user_id", how="left")
        df["hours_since_first_touchpoint"] = df.apply(
            lambda x: (x["timestamp"] - x["first_touchpoint"]).total_seconds() / 3600, axis=1
        )
    else:
        df["is_activation"] = convert_timestamps(df, "is_activation")
        df["hours_since_first_touchpoint"] = df.apply(
            lambda x: (x["timestamp"] - x["is_activation"]).total_seconds() / 3600, axis=1
        )

    if (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 3600 < (24 * 90):
        st.warning(
            "The date range of the provided data is too short. The analysis may not be accurate and some plots may not be displayed."
        )

    days_list = [1, 3, 7, 14, 30, 60, 90, 180]

    df["value"] = df["value"].fillna(0)
    df = df[["user_id", "timestamp", "is_activation", "value", "hours_since_first_touchpoint"]].copy()

    return df, days_list


@st.cache_data
def prepare_plots(df, days_list):
    """Prepare plots for the analysis."""

    # days_list = [1, 3, 7, 14, 30, 60, 90, 180]
    # days_list = [1, 3, 7, 14, 30, 60]

    # Create new dataframe with aggregated payment values
    df_aggregate_payments = pd.DataFrame(df["user_id"].unique(), columns=["user_id"])

    for day in days_list:
        conditional_subset = df[df["hours_since_first_touchpoint"] <= (24 * day)]
        tmp_df = conditional_subset.groupby(by="user_id")["value"].sum().reset_index(name=f"D{day}")

        df_aggregate_payments = df_aggregate_payments.merge(tmp_df, how="left", on="user_id")

    return df_aggregate_payments, days_list


st.set_page_config(initial_sidebar_state="expanded")

st.markdown("## How relevant is pLTV for you?")
st.markdown(
    """
        This tool analyzes whether your business could potentially benefit from pLTV modeling. 
        It demonstrates how user revenue patterns evolve over time and shows how effectively optimizing for this can have a significant impact on your average user revenue. 
        """
)


st.markdown(
    """
            *The tool requires a CSV file with user event logs. Each row should represent a unique event with the following columns: 
            **user_id**, **timestamp**, **is_activation**, and **value**.*
            """
)
st.write("")


st.markdown("**Choose your system for dataset extraction**")
options = ["Firebase", "AppsFlyer", "Shopify", "Other"]
selection = st.pills(
    "Choose your system for dataset extraction", options, selection_mode="single", label_visibility="collapsed"
)

if selection == "Firebase":
    st.markdown("BigQuery Code:")
    table_name = st.text_input(
        label="Define the name of your BQ source table (e.g. `project_name.dataset_name.table_name`)",
        value="",
        # help="Enter the ID of the source table that contains the data you would like to analyze."
    )

    sampling_on = st.toggle("Adjust sample size", False)
    if sampling_on:
        percentage = (
            st.slider(
                label="If you believe your output will be too large, you can use this to create a subsample of your entire user base.",
                min_value=0,
                max_value=100,
                value=100,
                # help="Select the percentage of users to sample."
            )
            / 100
        )
    else:
        percentage = 1

    column_names_on = st.toggle("Edit column names", False)
    if column_names_on:
        # Column Names Section
        st.markdown(
            "If you're not using the standard BQ column names, update the column names for the BigQuery code below according to your own schema."
        )

        # Column Name Inputs
        user_id = st.text_input(
            label="User ID Column",
            value="user_id",
            # help="Enter the column name that represents the `user_id` in your data table."
        )
        timestamp = st.text_input(
            label="Timestamp Column",
            value="event_timestamp",
            # help="Enter the column name that represents the timestamp in your data table."
        )
        first_touchpoint = st.text_input(
            label="First Touchpoint Column",
            value="user_first_touch_timestamp",
            # help="Enter the column name that represents the first touchpoint in your data table."
        )
        value = st.text_input(
            label="Value Column",
            value="event_value_in_usd",
            # help="Enter the column name that represents the value in your data table."
        )
    else:
        user_id = "user_id"
        timestamp = "event_timestamp"
        first_touchpoint = "user_first_touch_timestamp"
        value = "event_value_in_usd"

    path = f"""
    WITH filtered_data AS (
    SELECT
        {user_id} AS user_id,
        {timestamp} AS timestamp,
        TIMESTAMP_MICROS({first_touchpoint}) AS first_touchpoint,
        {value} AS value,
    FROM `{table_name}`
    WHERE {timestamp} BETWEEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY) 
        AND TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
        AND TIMESTAMP_MICROS({first_touchpoint}) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
    ),

    sample_users AS (
    SELECT DISTINCT
        user_id
    FROM filtered_data
    GROUP BY user_id
    HAVING RAND() < {percentage}
    )

    SELECT DISTINCT
        user_id,
        timestamp,
        CASE
            WHEN timestamp = first_touchpoint THEN TRUE
            ELSE FALSE
            END AS is_activation,
        value,
    FROM filtered_data source_table
    JOIN sample_users
    USING (user_id)
    """

    st.write("")
    st.code(path, language="sql")
    st.markdown("")


elif selection == "AppsFlyer":
    st.info("AppsFlyer schema is not yet supported. Please select another option.")
elif selection == "Other":

    st.write("")
    st.markdown("Data Requirements and Guidelines:")

    st.markdown(
        """
            **1. Data Format**
            - CSV format (separated by commas)
            - historical data of user events a year back from yesterday *(Note: Remember the first touchpoint of the user has to be within this period)*
            
            **2. Data Structure**
            - Columns
                - `user_id`: *string* - reflects a consistent user ID across your entire csv file.
                - `timestamp`: *datetime* - a reliable timestamp for each event included in your csv file.
                - `is_activation`: *boolean* - indicates if entry represents the first event of a user.
                - `value`: *float* - the revenue amount produced as part of the event. Even though this is just he value, make sure it is consistent from a currency perspective between all events.
            - Rows
                - Each row represents a unique event
        """
    )


elif selection == "Shopify":

    st.markdown("PostgreSQL Code:")
    sources_on = st.toggle("Edit source table names", False)
    if sources_on:
        shopify_order_source = st.text_input(
            label="Define the name of your source table for orders",
            value='"postgres"."zz_shopify_shopify"."stg_shopify__order"',
        )

        shopify_order_adjustment_source = st.text_input(
            label="Define the name of your source table for order adjustments",
            value='"postgres"."zz_shopify_shopify"."stg_shopify__order_adjustment"',
        )

        shopify_refund_source = st.text_input(
            label="Define the name of your source table for refunds",
            value='"postgres"."zz_shopify_shopify"."stg_shopify__refund"',
        )

        shopify_order_tag_source = st.text_input(
            label="Define the name of your source table for order tags",
            value='"postgres"."zz_shopify_shopify"."stg_shopify__order_tag"',
        )
    else:
        shopify_order_source = '"postgres"."zz_shopify_shopify"."stg_shopify__order"'
        shopify_order_adjustment_source = '"postgres"."zz_shopify_shopify"."stg_shopify__order_adjustment"'
        shopify_refund_source = '"postgres"."zz_shopify_shopify"."stg_shopify__refund"'
        shopify_order_tag_source = '"postgres"."zz_shopify_shopify"."stg_shopify__order_tag"'

    sampling_on = st.toggle("Adjust sample size", False)
    if sampling_on:
        percentage = (
            st.slider(
                label="If you believe your output will be too large, you can use this to create a subsample of your entire user base.",
                min_value=0,
                max_value=100,
                value=100,
                # help="Select the percentage of users to sample."
            )
            / 100
        )
    else:
        percentage = 1

    path = f"""
    WITH windows AS (
    SELECT 
        user_id,
        created_timestamp AS timestamp,
        row_number() OVER (
            PARTITION BY user_id
            ORDER BY created_timestamp
        ) AS customer_order_seq_number,
        (orders.total_price
            + COALESCE(order_adjustments_aggregates.order_adjustment_amount, 0)
            + COALESCE(order_adjustments_aggregates.order_adjustment_tax_amount, 0)
            - COALESCE(refund_aggregates.refund_subtotal, 0)
            - COALESCE(refund_aggregates.refund_total_tax, 0)) AS order_adjusted_total,
        refund_aggregates.refund_subtotal,
        order_tag.order_tags
    FROM {shopify_order_source} AS orders
    LEFT JOIN (
        SELECT 
            order_id, 
            source_relation, 
            SUM(amount) AS order_adjustment_amount, 
            SUM(tax_amount) AS order_adjustment_tax_amount
        FROM {shopify_order_adjustment_source}
        GROUP BY 1, 2
    ) AS order_adjustments_aggregates
    ON orders.order_id = order_adjustments_aggregates.order_id
    AND orders.source_relation = order_adjustments_aggregates.source_relation
    LEFT JOIN (
        SELECT 
            order_id, 
            source_relation, 
            SUM(subtotal) AS refund_subtotal, 
            SUM(total_tax) AS refund_total_tax
        FROM {shopify_refund_source}
        GROUP BY 1, 2
    ) AS refund_aggregates
    ON orders.order_id = refund_aggregates.order_id
    AND orders.source_relation = refund_aggregates.source_relation
    LEFT JOIN (
        SELECT 
            order_id, 
            source_relation, 
            STRING_AGG(DISTINCT CAST(value AS TEXT), ', ') AS order_tags
        FROM {shopify_order_tag_source}
        GROUP BY 1, 2
    ) AS order_tag
    ON orders.order_id = order_tag.order_id
    AND orders.source_relation = order_tag.source_relation
    WHERE orders.total_price IS NOT NULL
      AND NOT (order_tag.order_tags ILIKE '%test%') 
new_vs_repeat AS (
    SELECT 
        user_id,
        timestamp,
        CASE 
            WHEN customer_order_seq_number = 1 THEN TRUE
            ELSE FALSE
        END AS new_vs_repeat,
        CASE 
            WHEN refund_subtotal IS NOT NULL THEN -refund_subtotal 
            ELSE order_adjusted_total 
        END AS value
    FROM windows
    WHERE timestamp BETWEEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY) 
                        AND TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY) 
),
filtered_new_vs_repeat AS (
    SELECT *
    FROM new_vs_repeat
    WHERE new_vs_repeat = TRUE 
    UNION ALL
    SELECT r.*
    FROM new_vs_repeat r
    JOIN (
        SELECT user_id
        FROM new_vs_repeat
        WHERE new_vs_repeat = TRUE
    ) n
    ON r.user_id = n.user_id
    WHERE r.new_vs_repeat = FALSE
),
sample_users AS (
    SELECT 
        DISTINCT user_id
    FROM filtered_new_vs_repeat
    GROUP BY user_id
    HAVING RAND() < {percentage}
)
SELECT DISTINCT 
    user_id,
    timestamp,
    new_vs_repeat AS is_activation,
    value
FROM filtered_new_vs_repeat source_table
JOIN sample_users
USING (user_id)
    """

    st.write("")
    st.code(path, language="sql")
    st.markdown("")


if "data" not in st.session_state:
    st.session_state["data"] = None

st.write("")

st.markdown("**Optional**: Estimate the potential monetary lift")
with st.expander(label="To provide you with an accurate estimate, the following parameters are needed", expanded=True):

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        ad_spend_dropdown = [
            "Less than $100k",
            "$100k - $300k",
            "$300k - $600k",
            "$600k - $1M",
            "$1M - $1.5M",
            "$1.5M - $2M",
            "$3M - $10M",
            "More than $10M",
        ]

        avg_monthly_spend = st.selectbox(
            label="Select your ad spend range",
            options=ad_spend_dropdown,
            index=None,
            placeholder="Select an option",
            # label_visibility="collapsed",
        )

    with col2:
        roas_period = st.selectbox(
            label="Select the ROAS window",
            options=["D30", "D60", "D90", "D180"],
            index=None,
            placeholder="Example D60",
            # label_visibility="collapsed",
        )

    with col3:
        regular_roas = st.number_input(
            label="Enter your avg. ROAS",
            value=None,
            placeholder="Example 0.95",
            # label_visibility="collapsed",
        )

st.write("")

st.markdown("**Upload your data**")
uploaded_file = st.file_uploader("Upload your data", type="csv", label_visibility="collapsed")

st.write("")


col1, col2, col3 = st.columns([1, 1, 1])

with col2:
    st.markdown(
        """
        <style>
            div.stButton > button {
                padding-top: 25px !important;
                padding-bottom: 25px !important;
                background-color: #50CC6D;
                border-color: #50CC6D;
                font-size: 20px !important; /* Optional: Adjust font size */
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Create the button
    analysis_button = st.button(r"$\textsf{\Large Run Analysis}$", type="primary", use_container_width=True)


if uploaded_file is not None:
    df = load_data(uploaded_file)

    if analysis_button:
        df, days_list = preprocess_data(df)

        df_aggregate_payments, days_list = prepare_plots(df, days_list)

        st.session_state["df_aggregate_payments"] = df_aggregate_payments
        st.session_state["days_list"] = days_list

        if avg_monthly_spend is not None and roas_period is not None and regular_roas is not None:
            st.session_state["avg_monthly_spend"] = avg_monthly_spend
            st.session_state["roas_period"] = roas_period
            st.session_state["regular_roas"] = regular_roas

        if st.success("Data loaded successfully!"):
            time.sleep(2)
            st.switch_page("pages/page_2.py")
else:
    if analysis_button:
        st.info("Please upload a CSV file to proceed.")
