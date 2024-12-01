import streamlit as st
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import openai
from datetime import datetime
from openai import OpenAI
import os
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from typing import List, Literal
import json


_ = load_dotenv(find_dotenv()) 
openai.api_key  = os.environ['OPENAI_API_KEY']
client = OpenAI()
st.session_state.client = client


def hide_message():
    st.session_state.show_info = False

def greeting():
    """Generate random funny greeting when the app is initiated"""
    try:
        completion = client.chat.completions.create(
            model = "gpt-4o",
            temperature=1.2,#This task needs creativity more than acuracy
            messages=[
                {"role": "system", "content": """You are the manager of a to-do list application 
                 and your users need to finish tasks in their to-do lists.
                 Your job is to greet the user to refresh, recharge them.
                 Greet your users in a funny and quirky fashion like the examples below:
                 - Greetings, taskmaster! Shall we make those tasks disappear?
                 - Working-Maniac! Unleash your task-ninja powers! Let’s roll!
                 - Ah, the chosen one returns! Ready to fulfill your destiny (and your to-do list)?
                 - DUN-DUN-DUN! The Task Titan has entered the chat. Let’s crush it!
                 - Player 1, press Start! The quest for productivity begins now!
                 - Beware, To-Do Wizard! The task creatures await your magic!

                 Make sure you response is brief and no more than 10 words.
                """},
                { 
                    "role": "user",
                    "content": f"""
                    Greet me in a funny and quirky fashion please.            
                    """
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error when generating greeting: {str(e)}"

def task_name(new_todo):
    #Extract task name from user input
    """Extract deadline info if exists"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",#This task is simply so use mini
            temperature= 0,
            messages=[#system content is like general setting for coherency and user content for specific tasks
                {"role": "system", "content": """You are an assistant that extracts and analyze information
                 from user input. The user input will be about a task that needs to be done. Including what the task is,
                 and potentially its deadline and importance.
                 Your mission is to only summarize what the task is.
                 For example, 
                 if the user input is:
                 "Finish my experiement report before next Tuesday",
                 Then you should output:
                  "Experiment Report",
                 if the user input is:
                 "Read Lilian Weng's blogs"
                 Then you should output:
                 "Lilian Weng's Report"

                """},
                { 
                    "role": "user",
                    "content": f"""I have a task description as {new_todo}, please give a brief name of my task.
                    Even if my task description contains something like /Think of possible future AI services/, it is still considered as a valid task.
                    Keep in mind your response can not be longer than {new_todo}. If the task description does not contain information about what needs to be done,
                    simply return
                    Invalid Task                
                    """
                }
            ]
        )

        return completion.choices[0].message.content
    except Exception as e:
        return f"Could not extract deadline: {str(e)}"

def extract_deadline(new_todo):
    #Langchain has tutorials on extracting info which gives more reliable results
    #For this project I'll keep what I created first, so you see this primitive prompt engineering way
    """Extract deadline info if exists"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",#This task is simply so use mini
            temperature= 0,
            messages=[#system content is like general setting for coherency and user content for specific tasks
                {"role": "system", "content": """You are an assistant that extracts and analyze information
                 from user input. The user input will be about a task that needs to be done. Your job is to
                 extract information about that task's deadline. 
                 For example, 
                 if the user input is:
                 "Finish my experiement report before next Tuesday",
                 Then you should output:
                  "Next Tuesday",
                 if the user input is:
                 "Read blogs"
                 Then, because information of time limit was not mentioned, you should output:
                 "None"

                """},
                { 
                    "role": "user",
                    "content": f"""I have a task description as {new_todo}, please help me extract information about this task's
                    deadline. If you can't find deadline information, just output "None".
                    If you found deadline information, output only the deadline information.
                    
                    """
                }
            ]
        )

        return completion.choices[0].message.content
    except Exception as e:
        return f"Could not extract deadline: {str(e)}"


class PriorityItem(BaseModel):
    Task: str = Field(description="Name of the task")
    Priority: Literal["High", "Medium", "Low"] = Field(description="Priority level of the task")
    Explanation: str = Field(description="Concise explanation for the priority assignment")

    def dict(self, *args, **kwargs):
        return{
            "Task":self.Task,
            "Priority":self.Priority,
            "Explanation":self.Explanation
        }

class PriorityResponse(BaseModel):
    priority: List[PriorityItem] = Field(description="List of prioritized tasks")

    def to_dict(self):
        return {
            "priority": [item.dict() for item in self.priority]
        }

def get_priority_recommendations(todos):
    # Initialize the parser
    parser = PydanticOutputParser(pydantic_object=PriorityResponse)
    
    # Get the format instructions
    format_instructions = parser.get_format_instructions()
    
    completion = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {"role": "system", "content": """You are a sophisticated assistant adept at analyzing tasks and
             determining priorities. When you are asked to help decide priorities, always consider the following:
             - Urgency of each task. If provided, take the deadline of each task into consideration.
             - Importance. Analyze why the user needs to do a specific task and how important the task is.
             - Dependencies between tasks. One task could benefit from another task.
             - Resource Constraints. That means how much time, money, effort or any other resource the task would require

             Provide clear, concise priority recommendations with brief explanations.
             
             {format_instructions}
            """.format(format_instructions=format_instructions)},
            {
                "role": "user",
                "content": f"""Please analyze and prioritize these tasks: {todos} while paying attention to the following points:
                - Deadlines set by the user. Remember that the task itself may have higher weights than deadline in deciding priority. 
                - Connection between tasks. For example, task A may benefit from task B. So task B may have a higher priority than task A.
                - Ensure explanations are concise and constructive. Avoid unnecessary phrases like 'This task has medium priority' or 
                'Therefore this task is less important' since these are already indicated by the Priority field.
                """
            }
        ]
    )
    
    # Parse the response
    try:
        response = parser.parse(completion.choices[0].message.content)

        return response.to_dict()
    except Exception as e:
        raise ValueError(f"Failed to parse response: {str(e)}")
    
def update_priority():
    try:
        for task_rec in st.session_state.rec["priority"]:
            task_name = task_rec["Task"]
            priority = task_rec["Priority"]
            st.session_state.todos.loc[st.session_state.todos["Task"]==task_name, "Priority"]=priority
        return st.session_state.todos
    except Exception as e:
        return(f"Update failure: {str(e)}")


def main():
    #Important note: actually a consistent database is required so that even after this app was closed, the user infos are preserved
    #With streamlit alone, infos are only preserved across reruns.
    #Maybe connect with a Dadabase in AWS
    if 'greeting' not in st.session_state:
        st.session_state.greeting = greeting()

    st.title(st.session_state.greeting)
    st.write("### Priority recommendations from AI")
    
    # Initialize session state variables
    if 'todos' not in st.session_state:
        st.session_state.todos = pd.DataFrame(
        columns=['Task', 'Created', 'Deadline','Priority']
    )
    if 'rec' not in st.session_state:
        st.session_state.rec = ""


    #Form section for adding new tasks
    with st.form("add_todo"):
        new_todo = st.text_input(label= "Add a task, try including contexts like deadlines and incentives",placeholder="New task")
        #st.write('Try including detailed context like deadlines and incentives.')
        submitted = st.form_submit_button("Add")
    if submitted and new_todo:
            if new_todo in st.session_state.todos["Task"].values:
                st.warning("Task already exist")
            else:
                deadline = extract_deadline(new_todo)
                #st.info(deadline)
                new_task = pd.DataFrame({
                    'Task': [task_name(new_todo)],
                    'Created': [datetime.now().strftime("%m-%d")],
                    'Deadline':deadline,
                    'Priority': [""]
                })
                st.session_state.todos = pd.concat([st.session_state.todos, new_task], ignore_index=True)
                st.success("Task added successfully")

    if 'show_info' not in st.session_state:
        st.session_state.show_info = True
    

    if st.session_state.show_info:
    # Create a container for the message and button
        with st.container():
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.info("List will be ranked with Ai recommendation. But try click on column name to sort flexibly.")
            with col2:
                st.button("×", key="close_button", on_click=hide_message)

    place_holder = st.empty()
    #priority initialized with a str, so cannot compare str with int
    #sorted_df = st.session_state.todos.sort_values(by="Priority", ascending=True)
    place_holder.dataframe(st.session_state.todos)

    if not st.session_state.todos.empty:
        if st.button("Get Recommendations"):
            with st.spinner('Generating...'):
                st.session_state.rec = get_priority_recommendations(st.session_state.todos)

                if st.session_state.rec:
                    st.write(st.session_state.rec)
                    #st.write(type(st.session_state.rec))
            
            #if st.button("Update Priority List"):
            
            st.session_state.todos = update_priority()

            priority_order = ['High', 'Medium', 'Low']

            st.session_state.todos['Priority'] = pd.Categorical(
                st.session_state.todos['Priority'], 
                categories=priority_order, 
                ordered=True
            )
            

            # Sort the DataFrame by the Priority column
            sorted_todos = st.session_state.todos.sort_values(by='Priority', ascending=True)
            st.session_state.todos = sorted_todos 

            #sorted = st.session_state.todos.sort_values(by="Priority",ascending = True)
            #st.session_state.todos = sorted
            place_holder.dataframe(sorted_todos)
if __name__ == "__main__":
    main()

