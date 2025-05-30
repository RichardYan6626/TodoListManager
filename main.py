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


#initialize openai client
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


#Extract task name from user description
def task_name(new_todo):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",#This task is simply so use mini
            temperature= 0,
            messages=[#system content is like general setting for coherency and user content for specific tasks
                #Using few-shot prompting to ensure a brief and clean response
                {"role": "system", "content": """You are an assistant that extracts and analyze information
                 from user input. The user input will be about a task that needs to be done. Including what the task is,
                 and potentially its deadline and importance.
                 Your mission is to only summarize what the task is.
                 For example, 
                 if the user input is:
                 "Finish my experiement report before next Tuesday",
                 Then you should output:
                  "Experiment Report",
                

                """},
                { #Improved prompt to be shorter and works better
                    "role": "user",
                    "content": f"""I have a task description as {new_todo}, please give a brief name of my task.
                    Even if my task description is only a noun like mediation it can still considered as a valid task.
                    Keep in mind your response must be shorter than {new_todo}. If the task description does not contain information about what needs to be done,
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
    #Langchain has tutorials on extracting info which gives more reliable results using Pydantic schemas
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

    def to_dict(self):#For the final output format
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
            {"role": "system", "content": """You are a sophisticated AI assistant specialized in analyzing tasks and determining priorities. Your role is to provide clear, concise priority recommendations with brief explanations. When analyzing tasks and deciding priorities, always consider the following factors:
            - Urgency of each task, including deadlines if provided
            - Importance of the task and its impact
            - Dependencies between tasks
            - Resource constraints (time, money, effort, etc.)

             Here are the format instructions for your output:
             <format_instructions>
             {format_instructions}
             </format_instructions>
            """.format(format_instructions=format_instructions)},
            {
                "role": "user",
                "content": f"""Please analyze and prioritize these tasks: 
                <todos>
                {todos} 
                </todos>

                You should first generate explanations for the priorities, then generate the priority order for each task.
                When providing your analysis and recommendations:
                    1. Use the format specified in the format instructions.
                    2. Ensure that your explanations are clear, concise, and directly related to the priority level you've assigned.
                    3. If there are dependencies or connections between tasks, mention these in your explanations.
                    4. Consider both short-term urgency and long-term importance when assigning priorities.
                    5. If resource constraints are a significant factor in prioritization, include this in your reasoning.
                    6. Avoid unnecessary descriptions in your explanation part that is evident and redundant like "This task has high priority"
                    7. Avoid starting your explanation in plain ways like  "This task..."

                    Remember to provide a holistic view of the task list, ensuring that your prioritization makes sense not just for individual tasks,
                    but for the entire set of tasks as a whole. Your goal is to help the user understand the most effective order in which to approach their tasks, based on a comprehensive analysis of all relevant factors.
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
            st.session_state.todos.loc[st.session_state.todos["Task"]==task_name, "Priority"]=priority #update priority column of dataframe
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


    # Initialize input state if not exists
    if 'task_input' not in st.session_state:
        st.session_state.task_input = ""
        
    #Form section for adding new tasks
    with st.form("add_todo"):
        new_todo = st.text_input(
            label="Add task by inputing a rough description, include context like deadline if possible",
            placeholder="New task",
            value=st.session_state.task_input,
            key="task_input_field"
        )

        submitted = st.form_submit_button("Add")
    if submitted and new_todo:
            if task_name(new_todo) in st.session_state.todos["Task"].values:
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
                # Clear the input field after successful submission
                st.session_state.task_input = ""

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

            place_holder.dataframe(sorted_todos)
if __name__ == "__main__":
    main()

