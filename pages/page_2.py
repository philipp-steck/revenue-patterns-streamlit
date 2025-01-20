import streamlit as st
import pandas as pd
import numpy as np
from streamlit_extras.stylable_container import stylable_container

def compute_correlation(df_aggregate_payments):
    """Compute the correlation between the aggregated payment values at each day"""
    correlation_matrix = df_aggregate_payments.loc[:, ~df_aggregate_payments.columns.isin(['user_id'])].corr(method='spearman')
    return correlation_matrix

def find_value_above_threshold(dictionary, threshold):
    """Find the first key in a dictionary that has a value above a threshold"""
    for key, value in dictionary.items():
        if (value > threshold) and (key != max_value):
            return key, value
    return None, None

def assign_factor(max_value, test_value):
    """Assign a factor based on the correlation value"""
    if max_value == 62: # 60
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
    elif max_value == 93: # 90
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
    elif max_value == 186: # 180
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

st.set_page_config(
    initial_sidebar_state="expanded"
)

st.markdown("## Here's what we can do for you")
st.markdown('''<div style="text-align: justify;">
    Based on the analysis of your data, Churney should be able to deliver the following results for your business:
    </div>''', unsafe_allow_html=True)

if 'df_aggregate_payments' not in st.session_state:
    st.write('')
    st.warning("To get up and running, please upload your data on the main page.")
    st.stop()
else:
    df_aggregate_payments = st.session_state['df_aggregate_payments']
    days_list = st.session_state['days_list']
    avg_ad_spend = st.session_state['avg_yearly_spend']
    roas_period = st.session_state['roas_period']
    regular_roas = st.session_state['regular_roas']

avg_ad_spend_monthly = avg_ad_spend / 12
if avg_ad_spend_monthly > 200000:
    avg_spending_factor = 0.03
elif avg_ad_spend_monthly > 100000:
    avg_spending_factor = 0.05
else:
    avg_spending_factor = 0


regular_roas = regular_roas / 100 # convert to decimal

correlation = compute_correlation(df_aggregate_payments)
relevant_values = {}

max_value = max(days_list)

for i, day in enumerate(days_list[::-1]):
        relevant_values[day] = correlation[f'D{day}'][f'D{max_value}']
        
churney_roas_period, churney_roas = find_value_above_threshold(relevant_values, 0.85)


correlation_factor = assign_factor(max_value, churney_roas)
churney_baseline = 0.1

current_return = avg_ad_spend * regular_roas
current_return_monthly  = (avg_ad_spend / 12) * regular_roas
churney_roas = regular_roas + regular_roas * (churney_baseline + avg_spending_factor + correlation_factor)
churney_return = avg_ad_spend * churney_roas
churney_return_monthly = (avg_ad_spend / 12) * churney_roas
uplift = churney_return - current_return
uplift_monthly = churney_return_monthly - current_return_monthly


st.write('')
st.write('')

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
            <b>Current {roas_period} returns</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="font-size: 2em; color: black; font-weight: Normal; text-align: left;">
            $ {current_return:,.0f}
            </div>
            """,
            unsafe_allow_html=True,
        )
      
        st.write('')

        st.markdown(
            f"""
            <div style="color: black;">
            <b>{roas_period} returns with Churney</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="font-size: 2em; color: black; font-weight: Normal; text-align: left;">
            $ {churney_return:,.0f}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write('')

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
            <b>Churney yearly increment improvement</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="font-size: 2em; color: white; font-weight: Normal; text-align: left;">
            $ {uplift:,.0f} <span style="font-size: 0.5em;">({(uplift/current_return)*100:.0f}%)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write('')

        st.markdown(
            """
            <div style="color: white;">
            <b>Churney monthly increment improvement</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="font-size: 2em; color: white; font-weight: Normal; text-align: left;">
            $ {uplift_monthly:,.0f} <span style="font-size: 0.5em;">({(uplift_monthly/current_return_monthly)*100:.0f}%)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write('')

st.markdown('''<div style="text-align: justify;">
    Proceed to the next screens to learn more about why we believe we can deliver these results, and how much value you can derive by adopting pLTV for your specific business.
    </div>''', unsafe_allow_html=True)

st.write('')
col1, col2, col3 = st.columns([5, 1, 1])

with col3:
    next = st.button("Next")
if next:
    st.switch_page("pages/page_3.py")