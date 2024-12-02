import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px


def plot_2(df_aggregate_payments, days_list):
    """Generate and display a line plot with percentage of users who made a purchase over time"""
    def calculate_percentage_payments(dataframe, column_name):
        if metric == 'Conversions':
            conversions = (dataframe[column_name] > 0).astype(int)
            percentage = conversions.mean() * 100
        else:
            percentage = dataframe[column_name].mean()
        
        return percentage
    
    percentage_payment = []

    df_aggregate_payments2 = df_aggregate_payments.copy()
    df_aggregate_payments2['all_zero'] = df_aggregate_payments2.drop(columns='user_id').eq(0).all(axis=1)
    df_aggregate_payments2 = df_aggregate_payments2[df_aggregate_payments2['all_zero']==False].copy()

    for i, day in enumerate(days_list):
        percentage = calculate_percentage_payments(df_aggregate_payments2, f'D{day}')
        percentage_payment.append(percentage)

    df_plot2 = pd.DataFrame(list(zip(days_list, percentage_payment)),
                            columns=['days', 'percentage'])
    
    if metric == 'Conversions':
        y_label = 'Share of total conversions (%)'
    else:
        y_label = 'Average revenue per user'


    fig = px.line(df_plot2, x='days', y='percentage', markers=True,
            template="simple_white",  title=None, labels={'percentage':y_label}
            )
  

    fig.update_xaxes(range=[0, df_plot2['days'].max()], showspikes=True, spikedash="dot", spikethickness=2, spikemode="toaxis")#spikesnap="data")
    fig.update_yaxes(showspikes=True, spikedash="dot", spikethickness=2, spikemode="toaxis", )#spikesnap="data")

    st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False})


    return df_plot2

st.set_page_config(
    initial_sidebar_state="expanded" 
)

st.markdown('## Post-Optimization Conversions')
st.markdown('''<div style="text-align: justify;">
    This feature represents conversion patterns over time, helping customers identify the volume of valuable users whose conversions occur after the typical 3-day optimization window. 
    Using cumulative conversion rates, the chart compares key time windows (e.g. 1, 3, 7, 14, 31, 62, 93, 186) 
    and highlights delayed conversions often missed in standard ad network optimizations. 
    By visualizing the increase in conversions beyond the 3-day mark, this tool helps businesses uncover missed opportunities to better optimize for long-term customer value.
    </div>''', unsafe_allow_html=True)

if 'df_aggregate_payments' not in st.session_state:
    st.write('')
    st.warning("To get up and running, please upload your data on the main page.")
    st.stop()
else:
    df_aggregate_payments = st.session_state['df_aggregate_payments']
    days_list = st.session_state['days_list']

st.divider()
metric = st.radio("", ('Conversions', 'Revenue'))      
plot_2(df_aggregate_payments, days_list)
st.write('')
if st.button("Next insight"):
    st.switch_page("pages/page_4.py")
elif st.button("Previous insight"):
    st.switch_page("pages/page_2.py")
