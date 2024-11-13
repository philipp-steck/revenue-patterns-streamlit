import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import matplotlib.pyplot as plt
import seaborn as sns
import re

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


    current_timestamp = pd.Timestamp.now()
    df = df[df['first_touchpoint'] < current_timestamp - pd.Timedelta(hours=(24*180))]
    
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

st.markdown("#### How relevant is pLTV for you?")
st.markdown("""
        This tool analyzes whether your business could potentially benefit from pLTV modeling. 
        It demonstrates how user revenue patterns evolve over time and shows how effectively optimizing for this can have a significant impact on your average user revenue. 
        We support some standard schemas and can help you wish querying your own data.
        """)

if 'data' not in st.session_state:
    st.session_state['data'] = None

table_schema = st.radio("**Step1**: Select your preferred schema or data source", ["Firebase exported through BQ", "Other data sources & schemas"], index=None) # "AppsFlyer raw data export"

if table_schema == "Firebase exported through BQ":
    st.markdown("""
        In case you haven’t, you can [export your project data from Firebase into BigQuery](https://firebase.google.com/docs/projects/bigquery-export). 
        With BigQuery, you can then analyze your data with BigQuery SQL or export the data to use with this tool. 
        This is [true also for GA4](https://support.google.com/analytics/answer/7029846#tables&zippy=). Once you have your data available in BQ, you can proceed to use this tool to tag your event names, and copy the output query so you can later upload the csv output of the query for analysis. 
    """ , unsafe_allow_html=True)
    with st.expander("Generate a BQ query you can easily upload for analysis", expanded=True):
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

        anchor_on = st.toggle("Include custom anchoring event", False)
        if anchor_on:
            anchoring_event = st.text_input(
            label="An event that best represent what you consider as potential first interaction of the user with your business. This could be a session, an install, or a purchase event - whichever best represents a first interaction. (comma-separated and enclosed in single quotes e.g. `'trial_start'`)",
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

    uploaded_file = st.file_uploader("**Step 2**: Upload your CSV data file", type="csv")

    if uploaded_file is not None:
        df = load_data(uploaded_file)
        column_names_check(df)
        on = st.toggle("**Optional**: Select your custom anchor event from your dataset", False)
        if on:
            option = st.selectbox("Pick one event", df['event'].unique())
        else:
            option = 'first_touchpoint'

elif table_schema == "Other data sources & schemas":
    with st.expander("Data Requirements and Guidelines", expanded=True):
    
        st.markdown("""
            You can choose to upload your own data .csv output carrying user event logs in a pre-defined time range where each row represents a unique event, 
            including a user identification, an interaction timestamp, a first touchpoint timestamp, an event name, and a revenue value.
                                
            First interaction of the user could be a first session, an install, or a purchase event - whichever best represents a first interaction.
            It's important to include only users in the table that have their first interaction within this pre-defined time range.
            
            **1. Data Format**
            - CSV format (separated by commas)
            - historical data of user events a year back from yesterday *(Note: Remember the first touchpoint of the user has to be within this period)*
            
            **2. Data Structure**
            - Columns
                - `user_id`: *string* - reflects a consistent user ID across your entire csv file.
                - `timestamp`: *datetime* - a reliable timestamp for each event included in your csv file.
                - `first_touchpoint`: *datetime* - the timestamp of the first interaction of the user with your brand or business.
                - `event`: *string* - the name of the reported event.
                - `value`: *float* - the revenue amount produced as part of the event. Even though this is just he value, make sure it is consistent from a currency perspective between all events.
            - Rows
                - Each row represents a unique event
        """)
        st.markdown("")

    uploaded_file = st.file_uploader("**Step 2**: Upload your CSV data file", type="csv")

    if uploaded_file is not None:
        df = load_data(uploaded_file)
        column_names_check(df)
        on = st.toggle("**Optional**: Select your custom anchor event from your dataset", False)
        if on:
            option = st.selectbox("Pick one event", df['event'].unique())
        else:
            option = 'first_touchpoint'

        if st.button('Run analysis'):
            df = preprocess_data(df, option)
            
            df_aggregate_payments, days_list = prepare_plots(df)

            st.session_state['df_aggregate_payments'] = df_aggregate_payments
            st.session_state['days_list'] = days_list
            
            if st.success('Data loaded successfully!'):
                time.sleep(2)
                st.switch_page("pages/page_2.py")
        




