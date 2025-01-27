import numpy as np
import pandas as pd
import streamlit as st
from streamlit_extras.stylable_container import stylable_container


def compute_correlation(df_aggregate_payments):
    """Compute the correlation between the aggregated payment values at each day"""
    correlation_matrix = df_aggregate_payments.loc[:, ~df_aggregate_payments.columns.isin(["user_id"])].corr(
        method="spearman"
    )
    return correlation_matrix


def find_value_above_threshold(dictionary, threshold):
    """Find the first key in a dictionary that has a value above a threshold"""
    for key, value in dictionary.items():
        if (value > threshold) and (key != max_value):
            return key, value
    return None, None


def assign_factor(max_value, test_value):
    """Assign a factor based on the correlation value"""
    if max_value == 60:
        if test_value < 0.4:
            factor = 0.1
        elif test_value < 0.6:
            factor = 0.08
        elif test_value < 0.7:
            factor = 0.03
        elif test_value < 0.8:
            factor = 0.01
        else:
            factor = 0
    elif max_value == 90:
        if test_value < 0.4:
            factor = 0.12
        elif test_value < 0.6:
            factor = 0.10
        elif test_value < 0.7:
            factor = 0.04
        elif test_value < 0.8:
            factor = 0.01
        else:
            factor = 0
    elif max_value == 180:
        if test_value < 0.4:
            factor = 0.14
        elif test_value < 0.6:
            factor = 0.12
        elif test_value < 0.7:
            factor = 0.04
        elif test_value < 0.8:
            factor = 0.01
        else:
            factor = 0
    return factor


def range_mapping(avg_ad_spend):
    spend_ranges = {
        "Less than $100k": (1, 100000),
        "$100k - $300k": (100000, 300000),
        "$300k - $600k": (300000, 600000),
        "$600k - $1M": (600000, 1000000),
        "$1M - $1.5M": (1000000, 1500000),
        "$1.5M - $3M": (1500000, 3000000),
        "$3M - $10M": (3000000, 10000000),
        "More than $10M": (10000000, 100000000),
    }

    return spend_ranges.get(avg_ad_spend, (None, None))


def get_avg_spending_factor(avg_ad_spend_monthly):
    if avg_ad_spend_monthly > 200000:
        return 0.03
    elif avg_ad_spend_monthly > 100000:
        return 0.05
    else:
        return 0


st.set_page_config(initial_sidebar_state="expanded")

st.markdown("## Here's what we can do for you")
st.markdown(
    """<div style="text-align: justify;">
    Based on the analysis of your data, Churney should be able to deliver the following results for your business:
    </div>""",
    unsafe_allow_html=True,
)

if "df_aggregate_payments" not in st.session_state:
    st.write("")
    st.warning("To get up and running, please upload your data on the main page.")
    st.stop()
if (
    "avg_monthly_spend" not in st.session_state
    or "roas_period" not in st.session_state
    or "regular_roas" not in st.session_state
):
    st.write("")
    st.warning(
        "To estimate the potential uplift, please use the form on the main page to provide your average yearly spend, ROAS period, and regular ROAS."
    )
    df_aggregate_payments = st.session_state["df_aggregate_payments"]
else:
    df_aggregate_payments = st.session_state["df_aggregate_payments"]
    days_list = st.session_state["days_list"]
    avg_ad_spend = st.session_state["avg_monthly_spend"]
    roas_period = st.session_state["roas_period"]
    regular_roas = st.session_state["regular_roas"]

    # average monthly ad spend
    ad_spend_range = range_mapping(avg_ad_spend)
    ad_spend_min = ad_spend_range[0]
    ad_spend_max = ad_spend_range[1]

    # average spending factor
    avg_spending_factor_min = get_avg_spending_factor(ad_spend_min)
    avg_spending_factor_max = get_avg_spending_factor(ad_spend_max)

    # Get correlation value/period from correlation matrix
    correlation = compute_correlation(df_aggregate_payments)
    relevant_values = {}

    max_value = max(days_list)

    for i, day in enumerate(days_list[::-1]):
        relevant_values[day] = correlation[f"D{day}"][f"D{max_value}"]

    churney_roas_period, churney_roas = find_value_above_threshold(relevant_values, 0.85)

    correlation_factor = assign_factor(max_value, churney_roas)

    # Churney baseline factor
    churney_baseline = 0.1

    churney_roas_min = regular_roas + regular_roas * (churney_baseline + avg_spending_factor_min + correlation_factor)
    churney_roas_max = regular_roas + regular_roas * (churney_baseline + avg_spending_factor_max + correlation_factor)

    # Compute output
    # 1. Compute min output
    min_return_monthly = ad_spend_min * regular_roas
    min_return_yearly = (ad_spend_min * 12) * regular_roas
    min_churney_return_monthly = ad_spend_min * churney_roas_min
    min_churney_return_yearly = (ad_spend_min * 12) * churney_roas_min
    min_uplift_monthly = min_churney_return_monthly - min_return_monthly
    min_uplift_yearly = min_churney_return_yearly - min_return_yearly
    min_percent_uplift_monthly = (min_uplift_monthly / min_return_monthly) * 100
    min_percent_uplift_yearly = (min_uplift_yearly / min_return_yearly) * 100

    # 2. Compute max output
    max_return_monthly = ad_spend_max * regular_roas
    max_return_yearly = (ad_spend_max * 12) * regular_roas
    max_churney_return_monthly = ad_spend_max * churney_roas_max
    max_churney_return_yearly = (ad_spend_max * 12) * churney_roas_max
    max_uplift_monthly = max_churney_return_monthly - max_return_monthly
    max_uplift_yearly = max_churney_return_yearly - max_return_yearly
    max_percent_uplift_monthly = (max_uplift_monthly / max_return_monthly) * 100
    max_percent_uplift_yearly = (max_uplift_yearly / max_return_yearly) * 100

    st.write("")
    st.write("")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Minimum ad spend value**")
        with stylable_container(
            key="container_with_border",
            css_styles="""
                    {
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        background-color: #F7F7F2;
                        border-radius: 20px;
                        padding: calc(1em - 1px)
                    }
                    """,
        ):
            with stylable_container(
                key="inner_container1",
                css_styles="""
                    {
                        background-color: #F7F7F2;
                        padding: calc(1em - 1px)
                    }
                    """,
            ):
                st.markdown(
                    f"""
                    <div style="color: black;">
                    Current monthly {roas_period} returns
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: black; font-weight: Normal; text-align: left;">
                    $ {min_return_monthly:,.0f}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write("")

                st.markdown(
                    f"""
                    <div style="color: black;">
                    Monthly {roas_period} returns with Churney
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: black; font-weight: Normal; text-align: left;">
                    $ {min_churney_return_monthly:,.0f}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write("")

            with stylable_container(
                key="inner_container2",
                css_styles="""
                    {
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        background-color: #50CC6D;
                        border-radius: 20px;
                        padding: calc(1em - 1px)
                    }
                    """,
            ):
                st.markdown(
                    """
                    <div style="color: white;">
                    Churney monthly increment improvement
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: white; font-weight: Normal; text-align: left;">
                    $ {min_uplift_monthly:,.0f} <span style="font-size: 0.5em;">{min_percent_uplift_monthly:.0f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write("")

                st.markdown(
                    """
                    <div style="color: white;">
                    Churney yearly increment improvement
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: white; font-weight: Normal; text-align: left;">
                    $ {min_uplift_yearly:,.0f} <span style="font-size: 0.5em;">{min_percent_uplift_yearly:.0f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col2:
        st.markdown("**Maximum ad spend value**")
        with stylable_container(
            key="container_with_border",
            css_styles="""
                    {
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        background-color: #F7F7F2;
                        border-radius: 20px;
                        padding: calc(1em - 1px)
                    }
                    """,
        ):
            with stylable_container(
                key="inner_container1",
                css_styles="""
                    {
                        background-color: #F7F7F2;
                        padding: calc(1em - 1px)
                    }
                    """,
            ):
                st.markdown(
                    f"""
                    <div style="color: black;">
                    Current monthly {roas_period} returns
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: black; font-weight: Normal; text-align: left;">
                    $ {max_return_monthly:,.0f}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write("")

                st.markdown(
                    f"""
                    <div style="color: black;">
                    Monthly {roas_period} returns with Churney
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: black; font-weight: Normal; text-align: left;">
                    $ {max_churney_return_monthly:,.0f}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write("")

            with stylable_container(
                key="inner_container2",
                css_styles="""
                    {
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        background-color: #50CC6D;
                        border-radius: 20px;
                        padding: calc(1em - 1px)
                    }
                    """,
            ):
                st.markdown(
                    """
                    <div style="color: white;">
                    Churney monthly increment improvement
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: white; font-weight: Normal; text-align: left;">
                    $ {max_uplift_monthly:,.0f} <span style="font-size: 0.5em;">{max_percent_uplift_monthly:.0f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write("")

                st.markdown(
                    """
                    <div style="color: white;">
                    Churney yearly increment improvement
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div style="font-size: 2em; color: white; font-weight: Normal; text-align: left;">
                    $ {max_uplift_yearly:,.0f} <span style="font-size: 0.5em;">{max_percent_uplift_yearly:.0f}%</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.write("")

st.write("")
col1, col2, col3 = st.columns([5, 1, 1])

with col3:
    next = st.button("Previous")
if next:
    st.switch_page("pages/page_4.py")
