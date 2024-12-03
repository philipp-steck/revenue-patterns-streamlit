import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import matplotlib.pyplot as plt
import seaborn as sns
import re

def load_data(uploaded_file):
    """Load data from a CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def column_names_check(df):
    """Check if the data meets the requirements."""
    required_columns = ['user_id', 'timestamp', 'is_activation', 'value']
    df_columns = df.columns.tolist()
    missing_columns = list(set(required_columns) - set(df_columns))

    # Initialize session state variables
    if 'success' not in st.session_state:
        st.session_state.success = False

    if set(required_columns).issubset(set(df_columns)):
        return True
    else:
       st.warning("The following required columns are missing: " + ", ".join(missing_columns) + ". Please check the requirements and upload the data again.")
       st.stop()


@st.cache_data
def preprocess_data(df, option):
    """Preprocess the data for analysis."""
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    if 'is_activation' not in df.columns:
        df['first_touchpoint'] = pd.to_datetime(df['first_touchpoint'])
        df['hours_since_first_touchpoint'] = (df['timestamp'] - df['first_touchpoint']).dt.total_seconds() / 3600
    else:
        df['is_activation'] = df['is_activation'].astype(bool)

        first_touchpoint = (
            df.loc[df.is_activation]
            .groupby('user_id')['timestamp']
            .min()
            .reset_index()
            .rename(columns={'timestamp': 'first_touchpoint'}).copy()
        )

        df = df.merge(first_touchpoint, on='user_id', how='left')
        df['hours_since_first_touchpoint'] = (df['timestamp'] - df['first_touchpoint']).dt.total_seconds() / 3600

    timestamp_now = pd.Timestamp.now()
    if df['timestamp'].iloc[0].tzinfo is not None:  
        current_timestamp = timestamp_now.tz_localize(df['timestamp'].iloc[0].tzinfo)
    else:
        current_timestamp = timestamp_now
        
    df = df[df['first_touchpoint'] < current_timestamp - pd.Timedelta(hours=(24*180))]
    # df = df[df['first_touchpoint'] <= current_timestamp - pd.Timedelta(hours=(24*62))]
    
    df['value'] = df['value'].fillna(0)


    return df

@st.cache_data
def prepare_plots(df):
    """Prepare plots for the analysis."""
    
    days_list = [1, 3, 7, 14, 31, 62, 93 , 186]
    # days_list = [1, 3, 7, 14, 31, 62]

    # Create new dataframe with aggregated payment values
    df_aggregate_payments = pd.DataFrame(df['user_id'].unique(), columns=['user_id'])

    for day in days_list:
        conditional_subset = df[df['hours_since_first_touchpoint'] <= (24*day)]
        tmp_df = conditional_subset.groupby(by='user_id')['value'].sum().reset_index(name=f'D{day}')

        df_aggregate_payments = df_aggregate_payments.merge(tmp_df, how='left', on='user_id')

    return df_aggregate_payments, days_list

st.set_page_config(
    initial_sidebar_state="expanded" 
)

st.markdown("## How relevant is pLTV for you?")
st.markdown("""
        This tool analyzes whether your business could potentially benefit from pLTV modeling. 
        It demonstrates how user revenue patterns evolve over time and shows how effectively optimizing for this can have a significant impact on your average user revenue. 
        """)

#st.info("""The tool requires a CSV file with user event logs. 
 #       Each row should represent a unique event with the following columns: 
  #     *user_id*, *timestamp*, *is_activation*, and *value*.
   #     """, icon="ℹ")
#st.write('')

st.markdown("""
            The tool requires a CSV file with user event logs. Each row should represent a unique event with the following columns: 
            *user_id*, *timestamp*, *is_activation*, and *value*.
            """)
st.write('')

st.markdown("#### Choose your system for dataset extraction")
options = ["Firebase", "AppsFlyer", "Shopify", "Other"]
selection = st.pills("Choose the system you're using", options, selection_mode="single", label_visibility="collapsed")

if selection == "Firebase":
    st.markdown("BigQuery Code:")
    table_name = st.text_input(
    label="Define the name of your BQ source table (e.g. `project_name.dataset_name.table_name`)",
    value='',
    # help="Enter the ID of the source table that contains the data you would like to analyze."
    )
        
    sampling_on = st.toggle("Adjust sample size", False)
    if sampling_on:
        percentage = st.slider(
            label="If you believe your output will be too large, you can use this to create a subsample of your entire user base.",
            min_value=0,
            max_value=100,
            value=100,
            # help="Select the percentage of users to sample."
        ) / 100
    else:
        percentage = 1

    column_names_on = st.toggle("Edit column names", False)
    if column_names_on:
        # Column Names Section
        st.markdown("If you're not using the standard BQ column names, update the column names for the BigQuery code below according to your own schema.")

        # Column Name Inputs
        user_id = st.text_input(
            label="User ID Column",
            value='user_id',
            # help="Enter the column name that represents the `user_id` in your data table."
        )
        timestamp = st.text_input(
            label="Timestamp Column",
            value='event_timestamp',
            # help="Enter the column name that represents the timestamp in your data table."
        )
        first_touchpoint = st.text_input(
            label="First Touchpoint Column",
            value='user_first_touch_timestamp',
            # help="Enter the column name that represents the first touchpoint in your data table."
        )
        value = st.text_input(
            label="Value Column",
            value='event_value_in_usd',
            # help="Enter the column name that represents the value in your data table."
        )
    else:
        user_id = 'user_id'
        timestamp = 'event_timestamp'
        first_touchpoint = 'user_first_touch_timestamp'
        value = 'event_value_in_usd'

    path = f'''
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
    '''
    
    st.write('')
    st.code(path, language='sql')
    st.markdown("")



elif selection == "AppsFlyer":
    st.info("AppsFlyer schema is not yet supported. Please select another option.")
elif selection == "Other":
    
    st.write('')
    st.markdown("Data Requirements and Guidelines:")

    st.markdown("""
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
        """)


elif selection == "Shopify":

    st.markdown("PostgreSQL Code:")
    sources_on = st.toggle("Edit source table names", False)
    if sources_on:
        shopify_order_source = st.text_input(
            label='Define the name of your source table for orders',
            value='"postgres"."zz_shopify_shopify"."stg_shopify__order"',
        )

        shopify_order_adjustment_source = st.text_input(
            label='Define the name of your source table for order adjustments',
            value='"postgres"."zz_shopify_shopify"."stg_shopify__order_adjustment"',
        )

        shopify_refund_source = st.text_input(
            label='Define the name of your source table for refunds',
            value='"postgres"."zz_shopify_shopify"."stg_shopify__refund"',
        )

        shopify_order_tag_source = st.text_input(
            label='Define the name of your source table for order tags',
            value='"postgres"."zz_shopify_shopify"."stg_shopify__order_tag"',
        )
    else:
        shopify_order_source = '"postgres"."zz_shopify_shopify"."stg_shopify__order"'
        shopify_order_adjustment_source = '"postgres"."zz_shopify_shopify"."stg_shopify__order_adjustment"'
        shopify_refund_source = '"postgres"."zz_shopify_shopify"."stg_shopify__refund"'
        shopify_order_tag_source = '"postgres"."zz_shopify_shopify"."stg_shopify__order_tag"'
        
    sampling_on = st.toggle("Adjust sample size", False)
    if sampling_on:
        percentage = st.slider(
            label="If you believe your output will be too large, you can use this to create a subsample of your entire user base.",
            min_value=0,
            max_value=100,
            value=100,
            # help="Select the percentage of users to sample."
        ) / 100
    else:
        percentage = 1

    path = f'''
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
    '''
    
    st.write('')
    st.code(path, language='sql')
    st.markdown("")


if 'data' not in st.session_state:
    st.session_state['data'] = None

st.write('')

st.markdown("#### Upload your data")
uploaded_file = st.file_uploader("Upload your data", type="csv", label_visibility="collapsed")

st.write('')

col1, col2, col3 = st.columns([1, 1, 1])

with col2:
    st.markdown("""
        <style>
            div.stButton > button {
                padding-top: 25px !important;
                padding-bottom: 25px !important;
                font-size: 20px !important; /* Optional: Adjust font size */
            }
        </style>
    """, unsafe_allow_html=True)

    # Create the button
    test = st.button(
        r"$\textsf{\Large Run Analysis}$",
        type="primary",
        use_container_width=True
    )


if uploaded_file is not None:
    df = load_data(uploaded_file)
    # column_names_check(df)
    option = 'first_touchpoint'

    if test:
        df = preprocess_data(df, option)
        
        df_aggregate_payments, days_list = prepare_plots(df)

        st.session_state['df_aggregate_payments'] = df_aggregate_payments
        st.session_state['days_list'] = days_list
        
        if st.success('Data loaded successfully!'):
            time.sleep(2)
            st.switch_page("pages/page_2.py")
else:
    if test:
        st.info("Please upload a CSV file to proceed.")



