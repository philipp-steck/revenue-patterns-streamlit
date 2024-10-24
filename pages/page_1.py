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

def column_names_check(df):
    """Check if the data meets the requirements."""
    required_columns = ['user_id', 'timestamp', 'first_touchpoint', 'event', 'value']
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
    df['first_touchpoint'] = pd.to_datetime(df['first_touchpoint'])

    if option != 'first_touchpoint':
        new_anchor = df.loc[df['event'] == f'{option}'].groupby('user_id')['timestamp'].min().reset_index(name='new_anchor_timestamp')
        df = pd.merge(df, new_anchor, on='user_id', how='right')
        df['hours_since_first_touchpoint'] = (df['timestamp'] - df['new_anchor_timestamp']).dt.total_seconds() / 3600
    else:
        df['hours_since_first_touchpoint'] = (df['timestamp'] - df['first_touchpoint']).dt.total_seconds() / 3600
    
    df['value'] = df['value'].fillna(0)

    return df

@st.cache_data
def prepare_plots(df):
    """Prepare plots for the analysis."""
    
    days_list = [1, 3, 7, 14, 31, 62, 93 , 186]

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

# st.title("How relevant is pLTV for you?")
# st.markdown("""
#    This tool analyses if your business potentially benefit from pLTV modeling.
#    It demonstrates how users revenue patterns evolve over time and show how effectively optimizing on it can have a large impact on your average user revenue.
# """)
st.markdown("#### Let's get started with the analysis!")

if 'data' not in st.session_state:
    st.session_state['data'] = None

table_schema = st.radio("Select a table schema", ["Firebase exported through BQ", "Other data sources & schemas"], index=None) # AppsFlyer raw data export

if table_schema == "Firebase exported through BQ":
    with st.expander("Create BigQuery code to generate data that can be used in the analysis tool", expanded=True):
        table_name = st.text_input(
            label="Source table (e.g. `project_name.dataset_name.table_name`)",
            value='',
            # help="Enter the ID of the source table that contains the data you would like to analyze."
        )
             
        sampling_on = st.toggle("Adjust sample size", False)
        if sampling_on:
            percentage = st.slider(
                label="Choose your sample size (% of population)?",
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
            st.markdown("If needed, you can change the column names for the BigQuery code below.")

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
            event = st.text_input(
                label="Event Column",
                value='event_name',
                # help="Enter the column name that represents the event in your data table."
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
            event = 'event_name'
            value = 'event_value_in_usd'

        anchor_on = st.toggle("Include custom anchoring events", False)
        if anchor_on:
            anchoring_event = st.text_input(
            label="Event names (comma-separated and enclosed in single quotes e.g. `'trial_start'`)",
            value=''
            )
            anchoring_event = f"({event} IN ({anchoring_event}) OR ({value} != 0 OR {value} IS NOT NULL))"
        else: 
            anchoring_event = f"({value} != 0 OR {value} IS NOT NULL)"

        path = f'''
        WITH filtered_data AS (
        SELECT
            {user_id} AS user_id,
            {timestamp} AS timestamp,
            TIMESTAMP_MICROS({first_touchpoint}) AS first_touchpoint,
            {event} AS event,
            {value} AS value,
        FROM `{table_name}`
        WHERE {timestamp} BETWEEN TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY) 
            AND TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
            AND TIMESTAMP_MICROS({first_touchpoint}) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
            AND {anchoring_event}
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
            first_touchpoint,
            event,
            value,
        FROM filtered_data source_table
        JOIN sample_users
        USING (user_id)
        '''
        
        st.write('')
        st.markdown("**BigQuery Code**")
        st.code(path, language='sql')
        st.markdown("")

elif table_schema == "Other data sources & schemas":
    with st.expander("Data Requirements and Guidelines", expanded=True):
        st.markdown("""
            To ensure the analysis runs smoothly with your own dataset, please make sure your data meets the following criteria:

            **1. Data Format**
            - CSV format (separated by commas)
            - historical data of user events a year back from yesterday *(Note: Remember the first touchpoint of the user has to be within this period)*
            
            **2. Data Structure**
            - Columns
                - `user_id`: *string*
                - `timestamp`: *datetime*
                - `first_touchpoint`: *datetime*
                - `event`: *string*
                - `value`: *float*
            - Rows
                - Each row represents a unique event
        """)
        st.markdown("")

if table_schema:
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        df = load_data(uploaded_file)
        column_names_check(df)
        on = st.toggle("Define custom anchoring event", False)
        if on:
            option = st.selectbox("Pick one event", df['event'].unique())
        else:
            option = 'first_touchpoint'

        if st.button('run analysis'):
            df = preprocess_data(df, option)
            st.write(df.head())
            
            df_aggregate_payments, days_list = prepare_plots(df)

            st.session_state['df_aggregate_payments'] = df_aggregate_payments
            st.session_state['days_list'] = days_list
            
            if st.success('Data loaded successfully!'):
                time.sleep(2)
                st.switch_page("pages/page_2.py")
    




