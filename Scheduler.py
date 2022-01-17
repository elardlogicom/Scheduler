# -*- coding: utf-8 -*-
"""
Created on Tue Nov 16 13:31:34 2021

@author: Elliot Lard
"""
from os import path
import seaborn as sns
import streamlit as st
import pandas as pd
from datetime import timedelta
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import datetime

@st.cache
def load_ticket_data(file):
    data = pd.read_csv(file, sep='\t')
    #Rename Columns
    data.rename(columns = {'CustomField.{Tier 1 Resolution}':'tier_1_resolution',
                    'CustomField.{Tier 2 Resolution}':'tier_2_resolution',
                    'CustomField.{Issue Code}':'issue_code',
                    'CustomField.{Call Center Agent}':'answered_by',
                    'CustomField.{Escalation}':'escalation',
                    'QueueName':'queue_name',
                    'Cc':'worked_by'},
                  inplace = True)
    #remove lowercases
    data.columns = data.columns.str.lower()
    
    #drop the rows that have no `started date
    data.drop(data[data['started'].str.contains('Not')].index,axis = 0, inplace = True)
    
    data['id']=str(data['id'])
    #convert date_times
    for i in ['created','started','resolved']:
        data[i] = pd.to_datetime(data[i])   
    
    #add duration columns
    data['created_started_minutes'] = (data['started']-data['created']).dt.total_seconds()/60
    data['created_resolved_minutes'] = (data['resolved']-data['created']).dt.total_seconds()/60
    data['started_resolved_minutes'] = (data['resolved']-data['started']).dt.total_seconds()/60
    return data
@st.cache
def load_subscriber_data(file):
    data = pd.read_csv(file)
    data.rename(columns = 
                       {'CustomerProduct Activation Date':'activation_date',
                        'CustomerProduct Description':'product_description',
                        'CustomerProduct Status':'product_status',
                        'Customer External ID':'account_number',
                        'Parent Name':'queue_name'},
                       inplace = True)
    data['queue_name'].replace({'TVIFIBER':'TVI-FIBER',
                                'Tombigbee':'FreedomFiber',
                                'TishoMingo':'Tishomingo',
                                'ACEPA':'ACE-FIBER',
                                'LREC':'RiverNetConnect',
                                'Prentiss Connect':'Prentiss',
                                'Central Access  (CAEC)':'Central'
                                }, inplace=True)
    #removed uppercase and spaces
    data.columns = data.columns.str.lower().str.replace(' ','_')
    #convert date column
    data['activation_date']=pd.to_datetime(data['activation_date'])
    return data

@st.cache
def staffing(data):
    
    staffing_table = pd.DataFrame(columns = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])

    for hour in range(0,24,1):
        entry = []

        for day in staffing_table.columns:
            subset = data.loc[((data['work_days'].str.contains(day))&
                                             (((data['start_time']-hour).between(-9,0))|
                                              ((data['start_time']-hour).between(15,23))))]
            entry.append(subset.shape[0])
        staffing_table = staffing_table.append(pd.Series(entry, staffing_table.columns), ignore_index = True)
    return staffing_table.apply(pd.to_numeric, errors='coerce')

@st.cache
def volume(ticket_data):
    volume_table = pd.DataFrame(columns = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])
    dayOfWeek={0:'Monday', 1:'Tuesday', 2:'Wednesday', 3:'Thursday', 4:'Friday', 5:'Saturday', 6:'Sunday'}
    for hour in range(0,24,1):
        entry = []

        for day in volume_table.columns:
            subset = ticket_data.loc[(ticket_data['created'].dt.hour == hour)&
                                     (ticket_data['created'].dt.dayofweek.map(dayOfWeek)==day)]
            entry.append(subset.shape[0])
        volume_table = volume_table.append(pd.Series(entry, volume_table.columns), ignore_index = True)
    return volume_table.apply(pd.to_numeric, errors='coerce')

@st.cache
def need(coverage_table):
    need_table = coverage_table.copy()
    for row in range(need_table.shape[0]):
        for column in range(need_table.shape[1]):
            indexes = np.array(range(row,(row+10),1))%24
            total = coverage_table.iloc[indexes,column].sum()
            need_table.iloc[row,column] = total
    return need_table

@st.cache
def needexp(staffing_table, volume_table, threshold = 3):
    
    need_table = ((volume_table/weeks)/threshold)-staffing_table
    
    
    return need_table

def heatmap(table,fmt='.4g'):
    fig, ax = plt.subplots(figsize = (6, 5))
    sns.heatmap(table, annot = True, fmt=fmt, cbar=False)
    times = pd.Series([12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    times[:12] = times[:12].astype('str')+' AM'
    times[12:] = times[12:].astype('str')+' PM'
    ax.set_yticklabels(times)
    plt.xticks(rotation = 25)
    st.pyplot(fig)


days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

st.title('Scheduler')
#load data



# =============================================================================
#%% Sidebar
# =============================================================================
with st.sidebar:
    with st.expander('Upload Data'):
        with st.form('upload data'):
            uploaded_ticket_data = st.file_uploader('Upload Ticket Data', accept_multiple_files=True)
            uploaded_subscriber_data = st.file_uploader('Upload Subscriber Data', accept_multiple_files=True)
            uploaded_schedule_data = st.file_uploader('Upload Schedule Data', accept_multiple_files=True)
            st.form_submit_button('upload data')

# =============================================================================
#%% Load and Clean Data
# =============================================================================
# Ticket Data
# data_load_state = st.text('Loading Ticket Data...')
if uploaded_ticket_data:
    files = []
    for file in uploaded_ticket_data:
        files.append(load_ticket_data(file))
    ticket_data = pd.concat(files)
elif path.exists('After_2021_10_1.tsv') and path.exists('Beginning-2021_10.tsv'):
    td1 = load_ticket_data('After_2021_10_1.tsv')
    td2 = load_ticket_data('Beginning-2021_10.tsv')
    ticket_data=pd.concat([td1,td2])
else:
    st.warning('Can not find ticket data files, please upload your data')
    st.stop()

# Subscriber Data
# data_load_state.text('Loading Subscriber Data...')
if uploaded_subscriber_data:
    files = []
    for file in uploaded_subscriber_data:
        files.append(load_subscriber_data(file))
    subscriber_data = pd.concat(files)
elif path.exists('All_T1_Subscribers_10-21.csv'):
    subscriber_data = load_subscriber_data('All_T1_Subscribers_10-21.csv')
else:
    st.warning('Can not find Subscriber data files, please upload your data')
    st.stop()

# Schedule Data
# data_load_state.text('Loading Schedule Data...')

if path.exists('saved_schedule.csv'):
    employee_schedules = pd.read_csv('saved_schedule.csv')
else:
    st.warning('Can not find Schedule data file, please upload your data')
    st.stop()

# data_load_state.text('Done')

# =============================================================================
#%% Sidebar Date Range
# =============================================================================
with st.sidebar:
    with st.expander('Choose Date Range'):        
        newest_ticket_date = ticket_data.created.max()-pd.to_timedelta('1 day')
        oldest_ticket_date = ticket_data.created.min()+pd.to_timedelta('1 day')
        start_date = pd.to_datetime(st.date_input('Start Date',newest_ticket_date,
                                                          min_value=oldest_ticket_date,max_value=newest_ticket_date))
        weeks = st.number_input('weeks',1,step=1)
        
        selected_data = ticket_data[
            (ticket_data.created<=start_date)&
            (ticket_data.created>=(start_date-timedelta(weeks=weeks)))]
        
        newest_ticket_date = selected_data.created.max()
        oldest_ticket_date = selected_data.created.min()
        
        created_minmax = (oldest_ticket_date.strftime('%m/%d/%Y'),newest_ticket_date.strftime('%m/%d/%Y'))
        st.write(str(created_minmax[0]) + ' - ' + str(created_minmax[1]))


with st.sidebar:
    with st.expander('Select and Save Schedule'):
        with st.form('upload schedule'):
            if uploaded_schedule_data:
                files = {}
                for file in uploaded_schedule_data:
                    files[file.name] = pd.read_csv(file)
                file_path = st.selectbox('schedule', files.keys())
            if st.form_submit_button('select'):
                files[file_path].to_csv('saved_schedule.csv', index = False)
                employee_schedules = pd.read_csv('saved_schedule.csv')
        # schedule_name = st.text_input('name of file')        
        st.download_button('Save Schedule', employee_schedules.to_csv(index = False).encode('utf-8'), st.text_input('name of file') + ".csv")

# =============================================================================
#%% add and delete employees
# =============================================================================
with st.expander('add edit or delete employees'):
    operation = st.selectbox('operation', ['add', 'edit', 'delete'])
    if operation == 'edit':
        index_name = st.selectbox('index to Operate on',employee_schedules['name'])
        index = employee_schedules[employee_schedules['name']==index_name].index[0]
        # index = st.selectbox('index to Operate on',range(0,employee_schedules.shape[0]))
    elif operation == 'delete':
        index = np.array(st.multiselect('index to Operate on',range(0,employee_schedules.shape[0]),default = [0]))
    with st.form('add_form'):
        if operation == 'add':
            add_button = st.form_submit_button('add entry')
            cols = st.columns(4)
            with cols[0]:
                name = st.text_input('Employee name')
            with cols[1]:
                email = st.text_input('Employee email')
            with cols[2]: start_time = st.slider('Shift start', 0, 23,8,1)
            with cols[3]: current = st.selectbox('Current', [True, False])
            work_days = st.multiselect('Work Days', days)
            
            entry = pd.Series([name, email, start_time, work_days, current], employee_schedules.columns)
            if add_button:
                employee_schedules = employee_schedules.append(entry, ignore_index = True)
        elif operation == 'edit':
            edit_button = st.form_submit_button('edit entry')
            cols = st.columns(4)
            with cols[0]:
                name = st.text_input('Employee name', employee_schedules.iloc[index]['name'])
            with cols[1]:
                email = st.text_input('Employee email', employee_schedules.iloc[index]['email'])
            with cols[2]: start_time = st.slider('Shift start', 0, 23,int(employee_schedules.iloc[index]['start_time']),1)
            with cols[3]: current = st.selectbox('Current', [True, False])
            index_work_days = []
            exec("index_work_days = "+employee_schedules.iloc[index]['work_days'])
            work_days = st.multiselect('Work Days', days, default = index_work_days)
            
            entry = pd.Series([name, email, start_time, work_days, current], employee_schedules.columns)
            if edit_button:
                employee_schedules.iloc[index] = entry
        elif operation == 'delete':
            delete_button = st.form_submit_button('delete entry')
            if delete_button:
                employee_schedules = employee_schedules.drop(index,axis=0)
            if len(index) != 0 and index.max() < employee_schedules.shape[0]:
                table_data = pd.DataFrame(employee_schedules.iloc[index]).astype(str)           
                table = st.table(table_data)    
    employee_schedules.to_csv('saved_schedule.csv', index = False)
    employee_schedules = pd.read_csv('saved_schedule.csv')    
    st.table(employee_schedules)

# =============================================================================
#%% Heatmaps
# =============================================================================

table_expander = st.expander('Tables')
if table_expander.expanded:
    with table_expander:
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
        table_select = st.radio('Table Type', ['Staffing', 'Ticket Volume', 'Coverage', 'Need'])
        current = st.radio('Current or Prospective', ['Current', 'Current + Planned'])
        if(current == 'Current'):
            selection = employee_schedules[employee_schedules['current']==True]
        else:
            selection = employee_schedules
        staffing_table = staffing(selection)
        volume_table = volume(selected_data)
        coverage_table = (volume_table/staffing_table)/weeks
        
        if table_select == 'Staffing':
            heatmap(staffing_table)
        elif table_select == 'Ticket Volume':
            heatmap(volume_table)
        elif table_select == 'Coverage':
            heatmap(coverage_table,'.2f')
        elif table_select == 'Need':
            threshold = st.number_input('Max Tickets Per Agent', 1,value=3)
            need_table = needexp(staffing_table,volume_table, threshold)
            heatmap(need_table, '.1f')

# for row in employee_schedules.iterrows():
#     st.text(row)

st.stop()
# =============================================================================
#%% Comparisons
# =============================================================================

with st.expander('comparisons'):
    schedules = st.file_uploader('upload schedule', accept_multiple_files=True)
    
    if schedules:
        choice = st.radio('chart type', ['staffing', 'coverage', 'need'],)
        cols = st.columns(len(schedules))
        if choice == 'staffing':
            for schedule, col in zip(schedules, cols):
                s = staffing(pd.read_csv(schedule))
                with col: heatmap(s)
        elif choice == 'coverage':
            for schedule, col in zip(schedules, cols):
                s = staffing(pd.read_csv(schedule))
                c = (volume_table/s)/weeks
                with col: heatmap(c,'.2f')
        elif choice == 'need':
            for schedule, col in zip(schedules, cols):
                s = staffing(pd.read_csv(schedule))
                c = (volume_table/s)/weeks
                n = need(c)
                with col: heatmap(n)