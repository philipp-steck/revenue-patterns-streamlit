import streamlit as st
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns

def plot_3(df_aggregate_payments, days_list):
    """Generate and display a heatmap plot for the percentile rank of users who made a purchase at day `reference` and `lookahead`"""
    st.divider()

    colA, colB = st.columns(2)
    with colA:
        reference = st.selectbox("Select a **reference day**", days_list, index=1)
    
    lookahead_list = [day for day in days_list if day >= reference]
    with colB:
        lookahead = st.selectbox(
            "Select a **lookahead day**",
            lookahead_list,
            index=lookahead_list.index(lookahead_list[-3])
        )

    bins = np.linspace(0, 1, 11)  # 10 bins from 0% to 100%
    labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}' for i in range(len(bins)-1)]

    df_aggregate_payments = df_aggregate_payments.sample(frac=1, random_state=42).reset_index(drop=True)
    temp_reference = df_aggregate_payments[df_aggregate_payments[f'D{reference}'] > 0].copy()
    temp_list = [num for num in days_list if num >= reference]
    df_reference = temp_reference[['user_id']].copy()

    for day in temp_list:
        df_reference[f'D{day}'] = temp_reference[f'D{day}'].rank(method='first', ascending=False).rank(pct=True, ascending=False)
        df_reference[f'D{day}'] = pd.cut(df_reference[f'D{day}'], bins=bins, labels=labels, include_lowest=True)

    heatmap_data = pd.crosstab(
        df_reference[f'D{reference}'],
        df_reference[f'D{lookahead}'],
        normalize='index'
    )

    heatmap_data = heatmap_data.loc[labels[::-1], labels]
    heatmap_data = heatmap_data * 10

    # Plot the heatmap
    fig, ax = plt.subplots(figsize=(10,8))
    sns.heatmap(
        heatmap_data,
        annot=True,
        cmap='Purples',
        cbar_kws={'shrink':0.75,'label': 'Movement between percentiles (%)'})

    plt.xlabel(f'Lookahead: Percentile rank of the same users after D{lookahead}')
    plt.ylabel(f'Reference: Initial percentile Rank of users on D{reference}')
    plt.yticks(rotation=0)
    st.pyplot(fig)

    st.write()
    container = st.container(border=False)
    container.markdown(f'''<div style="text-align: justify;">
    For example, customers who generated the most value by day seven may be lower-value customers by day 60—their ranking or relative importance compared to others may have changed. 
    This output quantifies the degree to which the relative ordering of valuable customers based on their early value differs from their later relative ordering after more time has passed. 
    It shows if the most important valuable customers early on remain the most important over a longer period.
    </div>''', unsafe_allow_html=True)
    container.write('')

st.set_page_config(
    initial_sidebar_state="expanded" 
)

st.markdown('## User Value Re-Ranking')
st.markdown('''<div style="text-align: justify;">
    The third output analyzes how the ranking or relative importance of valuable customers changes over time. 
    It looks at the customers who were identified as valuable early on, like up to day 3. 
    Then, it examines whether the ordering of those same customers based on how valuable they are has shifted by a later date, like day 60.
    </div>''', unsafe_allow_html=True)

if 'df_aggregate_payments' not in st.session_state:
    st.write('')
    st.warning("To get up and running, please upload your data on the main page.")
    st.stop()
else:
    df_aggregate_payments = st.session_state['df_aggregate_payments']
    days_list = st.session_state['days_list']

plot_3(df_aggregate_payments, days_list)
st.write('')

col1, col2, col3 = st.columns([5, 1, 1])

with col3:
    next = st.button("Previous")
if next:
    st.switch_page("pages/page_4.py")

