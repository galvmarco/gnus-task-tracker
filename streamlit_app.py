import streamlit as st
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Initialize DynamoDB connection
dynamodb = boto3.resource('dynamodb')
table_name = "TaskStatus"
table = dynamodb.Table(table_name)

# Function to initialize the database (DynamoDB will handle creating the table on AWS)
def init_db():
    try:
        # Check if the table exists by fetching a list of tables
        dynamodb.meta.client.describe_table(TableName=table_name)
    except ClientError as e:
        st.write("Error: ", e.response['Error']['Message'])

# Function to insert initial tasks for the current week
def insert_initial_tasks(tasks, start_date):
    for task in tasks:
        for i in range(7):
            task_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            try:
                table.put_item(
                    Item={
                        'task_name': task,
                        'task_date': task_date,
                        'status': 0  # Initially unchecked
                    }
                )
            except ClientError as e:
                st.write("Error inserting tasks: ", e.response['Error']['Message'])

# Function to fetch tasks for the current week
def get_tasks_for_week(start_date):
    tasks_for_week = []
    for i in range(7):
        task_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            response = table.scan(
                FilterExpression="task_date = :date",
                ExpressionAttributeValues={":date": task_date}
            )
            tasks_for_week.extend(response['Items'])
        except ClientError as e:
            st.write("Error fetching tasks: ", e.response['Error']['Message'])
    return tasks_for_week

# Function to update task status
def update_task_status(task_name, task_date, new_status):
    try:
        table.update_item(
            Key={
                'task_name': task_name,
                'task_date': task_date
            },
            UpdateExpression="set #s = :status",
            ExpressionAttributeValues={':status': new_status},
            ExpressionAttributeNames={'#s': 'status'}
        )
    except ClientError as e:
        st.write("Error updating task status: ", e.response['Error']['Message'])

# Initialize the database
init_db()

# Task list for example
tasks = ["Task A", "Task B", "Task C"]

# Define week navigation state
if 'current_week_start' not in st.session_state:
    st.session_state['current_week_start'] = datetime.now() - timedelta(days=datetime.now().weekday())

# Define functions to navigate weeks
def go_to_previous_week():
    st.session_state['current_week_start'] -= timedelta(weeks=1)

def go_to_next_week():
    st.session_state['current_week_start'] += timedelta(weeks=1)

def go_to_current_week():
    st.session_state['current_week_start'] = datetime.now() - timedelta(days=datetime.now().weekday())

# Display navigation buttons
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button('← Previous Week'):
        go_to_previous_week()
with col2:
    if st.button('Current Week'):
        go_to_current_week()
with col3:
    if st.button('Next Week →'):
        go_to_next_week()

# Insert initial tasks for current week
insert_initial_tasks(tasks, st.session_state['current_week_start'])

# Fetch tasks for the current week
tasks_for_week = get_tasks_for_week(st.session_state['current_week_start'])

# Create a grid-like table using the data fetched
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Display the table of tasks and check buttons
st.write("### Task Completion for the week starting:", st.session_state['current_week_start'].strftime('%Y-%m-%d'))
table_data = {}

for task in tasks:
    cols = st.columns(7)
    for i, day in enumerate(days_of_week):
        task_date = (st.session_state['current_week_start'] + timedelta(days=i)).strftime('%Y-%m-%d')
        task_entry = next((t for t in tasks_for_week if t['task_name'] == task and t['task_date'] == task_date), None)
        if task_entry:
            checked = st.checkbox(day, value=bool(task_entry['status']), key=f"{task}_{day}")
            table_data[(task, day)] = checked
            # Update database when the checkbox is toggled
            if checked != bool(task_entry['status']):
                update_task_status(task, task_date, int(checked))
