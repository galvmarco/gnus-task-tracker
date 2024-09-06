import streamlit as st
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Initialize DynamoDB connection
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
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
    with table.batch_writer() as batch:
        for task in tasks:
            for i in range(7):
                task_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                try:
                    batch.put_item(
                        Item={
                            'task_name': task,
                            'task_date': task_date,
                            'status': 0  # Initially unchecked
                        }
                    )
                except ClientError as e:
                    st.write("Error inserting tasks: ", e.response['Error']['Message'])


@st.cache_data(ttl=300)  # Cache data for 5 minutes (adjust as needed)
def get_tasks_for_week(start_date):
    tasks_for_week = []
    for i in range(7):
        task_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            response = table.query(
                KeyConditionExpression="task_date = :date",
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

# Fetch tasks for the current week
tasks_for_week = get_tasks_for_week(st.session_state['current_week_start'])

if not tasks_for_week:
    # Insert initial tasks for current week
    insert_initial_tasks(tasks, st.session_state['current_week_start'])
    tasks_for_week = get_tasks_for_week(st.session_state['current_week_start'])

# Create a grid-like table using the data fetched
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Display the table of tasks and check buttons
st.write("### Task Completion for the week starting:", st.session_state['current_week_start'].strftime('%Y-%m-%d'))

# Display weekdays as column headers and tasks as row headers
cols = st.columns(8)  # 7 columns for days of the week + 1 for task names

# The first column is reserved for task names, so we put an empty space for the header
cols[0].write("")

# Write days of the week as column headers
for i, day in enumerate(days_of_week):
    cols[i+1].write(day)

# Now create the checkboxes for each task under the appropriate day of the week
for task in tasks:
    row_cols = st.columns(8)  # 7 columns for days of the week + 1 for task names
    row_cols[0].write(task)  # Write the task name in the first column
    
    for i, day in enumerate(days_of_week):
        task_date = (st.session_state['current_week_start'] + timedelta(days=i)).strftime('%Y-%m-%d')
        task_entry = next((t for t in tasks_for_week if t['task_name'] == task and t['task_date'] == task_date), None)
        # Generate a unique key for the checkbox by including the task name, day, and the start date of the week
        key = f"{task}_{day}_{st.session_state['current_week_start'].strftime('%Y-%m-%d')}"
        
        if task_entry:
            checked = row_cols[i+1].checkbox("", value=bool(task_entry['status']), key=key)
            
            # Update database when the checkbox is toggled
            if checked != bool(task_entry['status']):
                update_task_status(task, task_date, int(checked))
