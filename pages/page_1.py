import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import matplotlib.pyplot as plt
import seaborn as sns

@st.cache_data
def load_data(uploaded_file):
    """Load data from a CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None
    
@st.cache_data    
def data_check(df):
    """Check if the data meets the requirements."""
    required_columns = ['user_id', 'timestamp', 'is_activation', 'value']
    df_columns = df.columns.tolist()

    if set(required_columns) != set(df_columns):
        st.warning('The uploaded data table format is incorrect. Please ensure the table has the required variables.', icon="⚠️")
        return False
    return True

@st.cache_data
def subsample_data(df):
    """Subsample the data to a smaller size if more than 500.000 rows."""
    if df.shape[0] > 500000:
        sampled_user_ids = (
            df['user_id']
            .drop_duplicates()
            .sample(frac=0.2, random_state=42)
        )
        df = df[df['user_id'].isin(sampled_user_ids)].copy()
    return df

@st.cache_data
def preprocess_data(df):
    """Preprocess the data for analysis."""
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None).dt.normalize()
    activation_dates = df.loc[df['is_activation'] == 1].groupby('user_id')['timestamp'].min().reset_index(name='activation_date')
    df = pd.merge(df, activation_dates, on='user_id', how='right')
    df['date_diff'] = (df['timestamp'] - df['activation_date']).dt.days.abs()
    df['date_diff'] = df['date_diff'].astype('Int64')
    df['value'] = df['value'].fillna(0)

    return df

@st.cache_data
def prepare_plots(df):
    """Prepare plots for the analysis."""
    days_list = [0, 1, 3, 7, 14, 31, 60, 90 , 180]

    # Create new dataframe with aggregated payment values
    df_aggregate_payments = pd.DataFrame(df['user_id'].unique(), columns=['user_id'])

    for day in days_list:
        conditional_subset = df[df['date_diff'] <= day]
        tmp_df = conditional_subset.groupby(by='user_id')['value'].sum().reset_index(name=f'D{day}')

        df_aggregate_payments = df_aggregate_payments.merge(tmp_df, how='left', on='user_id')

    return df_aggregate_payments, days_list

st.set_page_config(
    initial_sidebar_state="collapsed" 
)

st.title("How relevant is pLTV for you?")
st.markdown("""
    This tool analyses if your business potentially benefit from pLTV modeling.
    It demonstrates how users revenue patterns evolve over time and show how effectively optimizing on it can have a large impact on your average user revenue.
""")

with st.expander("Data Requirements and Guidelines"):
    st.markdown("""
        To ensure the analysis runs smoothly, please make sure your data meets the following criteria:

        **1. Data Format**
        - CSV format

        **2. Data Structure**
        - Columns
            - `user_id`: *string*
            - `timestamp`: *datetime*
            - `is_activation`: *int* (0 or 1)
            - `value`: *float*
        - Rows
            - Each row represents a unique event
    """)
    st.markdown("")

st.write('')

if 'data' not in st.session_state:
    st.session_state['data'] = None

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = load_data(uploaded_file)
    data_check(df)
    df = subsample_data(df)
    df = preprocess_data(df)
    df_aggregate_payments, days_list = prepare_plots(df)

    st.session_state['df_aggregate_payments'] = df_aggregate_payments
    st.session_state['days_list'] = days_list
    
    if st.success('Data loaded successfully!'):
        time.sleep(2)
        st.switch_page("pages/page_2.py")





