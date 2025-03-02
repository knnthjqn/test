import streamlit as st
import sqlite3
import random
import re
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

import openai
API_KEY = open("API_KEY.txt","r").read()
openai.api_key = API_KEY



def _get_message(entity):
    while True:
        user_input = input(f"{entity} Message: ")
        
        # Strip the input to remove any leading/trailing spaces
        if user_input.strip():
            # If the string is not empty after stripping, break out of the loop
            return user_input
        else:
            # Otherwise, ask again
            _get_message(entity)



def _ai_agent(user_input):
    completion = openai.chat.completions.create(
    model="gpt-4o-mini-2024-07-18",
    messages=[
            {"role": "system", "content": """
                    You are EJ, an impressive sales trainer agent for a telco company called DITO Telecomm. 
                    You are supervising a sales agent on his call and the goal is to close every conversation in 5-7 messages. Your messages are dedicated to the call center agent and not to the clien
                    You need to remember their conversation and provide suggestions to the agent on how to communicate with the client.
                    Once, appropriate advise him to for the account number, dont ever ask personal information.

                    Only make 2 comments that are super concise, solution-oriented, and in bullet-points. The chat is happening in real-time.
                    The comment should be in this format
                    - **topic**: message to agent

                    After resolving the case, ask the customer to rate the service from 1-5, 5 being the highest. use this message:
                    
                    - **Assure Prompt Resolution**: Mention explicitly how Arbolo AI prioritizes customer issues and provide a definitive timeline or steps on what happens next with their ticket.
                    - **Request Feedback**: Always close the conversation by inviting the customer to rate their service experience from 1-5 to gauge satisfaction and get valuable feedback.
                    
                    Don't show that message anymore once a rating is already provided. Don't answer questions that are not related to the company or to company business transactions. Limit the whole conversation from 6-10 messages only. Close it as fast as you can.

                    Remind the Agent to upsell or provide product recommendations if the concern is only a light complaint. Dont overexplain the product once the customer agrees or disagrees to buy it.
                    
                    
                    \n"""},
            {
                "role": "assistant",
                "content": user_input
            }
        ]
    )
    return completion.choices[0].message.content


def _ai_info_extractor(user_input):
    completion = openai.chat.completions.create(
    model="gpt-4o-mini-2024-07-18",
    messages=[
            {"role": "system", "content": """
                    get the relevant information asked. Your only source of information will be coming from the conversation given.
                    your answer should only be the information asked. no other fillers
                    \n"""},
            {
                "role": "user",
                "content": user_input
            }
        ]
    )
    return completion.choices[0].message.content


def _extract_info(call_recording, info=None):
    if info == "account number":
        return _ai_info_extractor(f"what is the customer or account number present in this conversation? {call_recording}. Return NULL if there are none.")
    elif (info=="rating") or (info=="rate"):
        return _ai_info_extractor(f"what is the rating that the customer give in this conversation? {call_recording}. Return NULL if there are none.")


def fetch_data(table_name):
    """
    Fetches and returns all records from the 'users' table.
    """
    import pandas as pd
    import sqlite3
    
    conn = sqlite3.connect("customerdb")
    cursor = conn.cursor()
    
    select_sql = f"SELECT * FROM {table_name}"
    cursor.execute(select_sql)
    
    rows = cursor.fetchall()
    conn.close()
    
    return pd.DataFrame(rows, columns=[_[0] for _ in cursor.description])

def _get_time_1yrago():
    import datetime
    
    # Get today's date
    today = datetime.date.today()
    
    # Subtract 365 days to approximate "one year ago"
    one_year_ago = today - datetime.timedelta(days=365)
    
    # Format as YYYY-MM-DD
    formatted_one_year_ago = one_year_ago.strftime("%Y-%m-%d")
    
    return str(formatted_one_year_ago)


def main():
    st.title("AI Agent") 

    def get_ai_response():
        return "This is a sample AI response."  
    


    cust_agent = 0
    running_msg = ["Hi. This is DITO Agent. How may I help you?"]
    call_log = {}
    msg_info = {"account number":'NULL',
                "rating":'NULL'}

    df_user = fetch_data("users")
    df_trans = fetch_data("transactions")
    df_grv =fetch_data("grievances")
    

    # AI Message Box
    ai_message = get_ai_response()
    st.text_area("AI Message:", ai_message, height=120, disabled=True)


    # Automatically refresh the app every 300 milliseconds
    st_autorefresh(interval=300, key="conversation_autorefresh")

    st.markdown("### Conversation")

    # Initialize conversation list and next role if they don't exist
    if "conversation" not in st.session_state:
        st.session_state.conversation = []  # start with an empty conversation

    if "next_role" not in st.session_state:
        st.session_state.next_role = "Customer"  # Conversation starts with the Customer
    
    if "customer_name" not in st.session_state:
        st.session_state["customer_name"] = "Unknown"

    if "customer_account" not in st.session_state:
        st.session_state["customer_account"] = "Unknown" 


    def extract_customer_info(message):
        # Extract account number (matches phrases like "account number" or "customer number" followed by digits)
        account_match = re.search(r"(?:account number|customer number)[^\d]*(\d+)", message, re.IGNORECASE)
        if account_match and msg_info["account number"] == 'NULL':
            msg_info["account number"] = account_match.group(1)

    # Extract rating (matches phrases like "rate", "rated", or "rating" followed by digits)
        rating_match = re.search(r"(?:rate(?:d)?|rating)[^\d]*(\d+)", message, re.IGNORECASE)
        if rating_match and msg_info["rating"] == 'NULL':
            msg_info["rating"] = rating_match.group(1)

        '''
        name_match = re.search(r"(?:my name is|i am|i'm|this is) (\w+)", message, re.IGNORECASE)
        age_match = re.search(r"(?:my age is|age is) (\d+)", message, re.IGNORECASE)
        education_match = re.search(r"(?:elementary|highschool|college) (\w+)", message, re.IGNORECASE)

        if name_match:
            st.session_state["first_name"] = name_match.group(1).strip()

        if age_match:
            st.session_state["age"] = age_match.group(1).strip()

        if education_match:
            st.session_state["education"] = education_match.group(1).strip()
        '''
    # Function that is called automatically when the text input changes (i.e. on Enter)
    def submit_message():
        msg = st.session_state["message_input"]
        if msg.strip():  # only add non-empty messages
            st.session_state["conversation"].append({
                "role": st.session_state["next_role"],
                "message": msg
            })

            # Check if the message contains customer info
            if st.session_state["next_role"] == "Customer":
                extract_customer_info(msg)

            # Toggle role
            st.session_state["next_role"] = "Agent" if st.session_state["next_role"] == "Customer" else "Customer"
        
            # Clear input field
            st.session_state["message_input"] = ""
    
    # Display conversation history in a text area
    conversation_text = "\n".join(
        [f"{entry['role']}: {entry['message']}" for entry in st.session_state["conversation"]]
    )

    # Use height and scroll position to ensure the latest message is visible
    #st.text_area("Conversation History", value=_initial_msg, height=200, disabled=True)
    st.text_area("Conversation History", value=conversation_text, height=200, disabled=True)

    # Text input for message
    st.text_input(f"Enter message as {st.session_state['next_role']}:", key="message_input", on_change=submit_message)


with st.sidebar:
    _initial_msg = "Hi. This is DITO Agent. How may I help you?"
    #options = ["Inbound", "Outbound"]
    #direction = st.segmented_control("Directions", options, label_visibility="collapsed")

    #Call Controls
    st.header("Call Customer")

    # Initialize session state variables if they don't exist
    if "phone_number" not in st.session_state:
        st.session_state.phone_number = ""

    if "initial_msg" not in st.session_state:
        st.session_state.initial_msg = ""

    if "conversation_log" not in st.session_state:
        st.session_state.conversation_log = ""

    if "first_name" not in st.session_state:
        st.session_state.first_name = ""

    if "age" not in st.session_state:
        st.session_state.age = ""

    if "education" not in st.session_state:
        st.session_state.education = ""

    if "account number" not in st.session_state:
        st.session_state["account number"] = ""

    if "rating" not in st.session_state:
        st.session_state.rating = ""

    if "ai_message" not in st.session_state:
        st.session_state.ai_message = ""

    if "conversation" not in st.session_state:
        st.session_state.conversation = []

    if "next_role" not in st.session_state:
        st.session_state["next_role"] = "Customer"  

    phone_number = st.text_input("Enter Phone Number:", st.session_state.phone_number)
    options = ["Call", "End Call", "Create Ticket"]
    direction = st.segmented_control("Directions", options, label_visibility="collapsed")

    def call():
        if not phone_number.isdigit():
            st.error("Please enter a valid phone number.")
        else:
            st.session_state.phone_number = phone_number
            # Update the session state variable that holds the initial message
            st.session_state.initial_msg = f"Calling {phone_number}..."
            st.success(st.session_state.initial_msg)
            
           

    def end_call():
        """Clears all fields when 'End Call' is pressed."""
        st.session_state.phone_number = ""
        st.session_state.customer_name = ""
        st.session_state.customer_account = ""
        st.session_state.ai_message = ""
        st.session_state.conversation = []  # Clear chat history
        st.success("Call ended.")

    def create_ticket():
        return random.randint(100000, 999999)
    
    # Initialize session state flag if not already set  
    if "ticket_created" not in st.session_state:
        st.session_state["ticket_created"] = False

    if direction == "Create Ticket":
        if "ticket_created" not in st.session_state or not st.session_state["ticket_created"]:
            # Generate ticket only if not already created in the current session
            st.session_state["ticket_number"] = create_ticket()
            st.session_state["ticket_created"] = True
            #st.success(f"Ticket created successfully! Ticket number: #{st.session_state['ticket_number']}")
        else:
            # Simply show the last generated ticket without extra messages
            st.write(f"Ticket number: #{st.session_state['ticket_number']}")
    else:
        # Reset the flag if another option is selected
        st.session_state["ticket_created"] = False

    # Check which option was selected
    if direction == "Call":
        call()
    elif direction == "End Call":
        end_call()

        #customer_name = "John Doe"
        #customer_email = "jo   hndoe@example.com"
        #customer_account = "123456789"

    # Display Customer Information using text_area (read-only)
    st.text_input("First Name:", value=st.session_state["first_name"], disabled=True)
    st.text_input("Age:", value=st.session_state["age"], disabled=True)
    st.text_input("Highest Educational Attainment:", value=st.session_state["education"], disabled=True)
    #st.text_input("Account Number:", value=st.session_state["account number"], disabled=True)
    #st.text_input("Rating:", value=st.session_state["rating"], disabled=True)


    # Placeholder for History section
    history_placeholder = st.empty()

    # Fetch history from database
    #history = fetch_history()

    # Extract the latest 3 entries
    #latest_entries = [entry for item in history for entry in item["entries"]][-3:]

    # Display in the placeholder container
    #with history_placeholder.container():
        #if latest_entries:
            #selection = st.segmented_control("History", latest_entries, label_visibility="collapsed")
        #else:
            #st.write("No history available.")


if __name__ == "__main__":
    main()
