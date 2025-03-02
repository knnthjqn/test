import streamlit as st
import openai
import sqlite3
import pandas as pd
import datetime
import random  # <-- Import the random module

# Set page configuration to use wide layout and expanded sidebar.
st.set_page_config(page_title="OSIRIS", layout="wide", initial_sidebar_state="expanded")

# Inject custom CSS to reduce margins/padding, hide scrollbars, scale down the interface,
# use a smaller font, and align the radio options horizontally.
st.markdown(
    """
    <style>
    /* Adjust main container to fit viewport and scale down */i
    .reportview-container .main .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
        padding: 0.3rem 0.5rem;
        max-width: 100%;
        margin: 0 auto;
        overflow: hidden;
        transform: scale(0.85);
        transform-origin: top left;
    }
    /* Hide scrollbars */
    ::-webkit-scrollbar {
        display: none;
    }
    body {
        overflow: hidden;
        font-size: 0.9rem;
    }
    /* Force radio buttons to display horizontally */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        gap: 1rem;
    }
    /* Style for AI suggestion text area: smaller font and height */
    textarea[aria-label="Suggestion"] {
        font-size: 0.9rem !important;
        height: 20px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load API key
with open("API_KEY2.txt", "r") as f:
    openai.api_key = f.read().strip()

# ---- Helper Functions ----

def _ai_agent(user_input):
    completion = openai.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": """
You are EJ, an impressive sales trainer agent for a telco company called DITO Telecomm. 
You are supervising a sales agent on his call and the goal is to close every conversation in 5-7 messages. Your messages are dedicated to the call center agent and not to the client.
You need to remember their conversation and provide suggestions to the agent on how to communicate with the client.
Once, appropriate advise him to for the account number, dont ever ask personal information.

Only make 2 comments that are 5-8 words only, solution-oriented, and in bullet-points. The chat is happening in real-time.
The comment should be in this format:
- **topic**: message to agent

After resolving the case, ask the customer to rate the service from 1-5, 5 being the highest. Use this message:

- **Request Feedback**: Always close the conversation by inviting the customer to rate their service experience from 1-5 to gauge satisfaction and get valuable feedback.

Don't show that message anymore once a rating is already provided. Don't answer questions that are not related to the company or to company business transactions. Limit the whole conversation from 6-10 messages only. Close it as fast as you can.

Remind the Agent to upsell or provide product recommendations if the concern is only a light complaint. Dont overexplain the product once the customer agrees or disagrees to buy it.
"""}, 
            {"role": "assistant", "content": user_input}
        ]
    )
    return completion.choices[0].message.content

def _ai_info_extractor(user_input):
    """
    Get information from conversation
    """
    completion = openai.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": """
Get the relevant information asked. Your only source of information is the conversation provided.
Your answer should only contain the information requested, with no fillers.
"""}, 
            {"role": "user", "content": user_input}
        ]
    )
    return completion.choices[0].message.content

def _extract_info(call_recording, info=None):
    """
    Get customer account and rating
    """
    if info == "account number":
        return _ai_info_extractor(f"what is the customer or account number present in this conversation? {call_recording}. Return NULL if there are none.")
    elif info == "rating" or info == "rate":
        return _ai_info_extractor(f"what is the rating that the customer give in this conversation? {call_recording}. Return NULL if there are none.")

def fetch_data(table_name):
    """Fetches all records from the given table in the 'customerdb' SQLite database."""
    conn = sqlite3.connect("customerdb")
    cursor = conn.cursor()
    select_sql = f"SELECT * FROM {table_name}"
    cursor.execute(select_sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=columns)

def _get_time_1yrago():
    """
    get date 1 year ago
    """
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    return one_year_ago.strftime("%Y-%m-%d")

# ---- Customer Data Update Function ----
def check_and_update_customer_data():
    """
    Checks if an account (or customer) number is mentioned in the conversation.
    If found and not already processed, it fetches customer info from the database
    and updates the sidebar with First Name, Age, Highest Education, Recommended Product,
    and the last 3 transactions/grievances.
    Once detected, the account number remains on display.
    """
    if st.session_state.get("customer_data_populated", False):
        pass

    conversation_text = ""
    for msg in st.session_state.conversation:
        conversation_text += f"{msg['role']}: {msg['message']}\n"
    
    account_number_candidate = None
    
    for msg in st.session_state.conversation:
        text = msg['message'].strip()
        if text.isdigit():
            account_number_candidate = text
            break
    
    if not account_number_candidate:
        if ("account number" in conversation_text.lower() or "customer number" in conversation_text.lower()):
            account_number_candidate = _extract_info(conversation_text, info="account number").strip()
    
    if account_number_candidate and account_number_candidate.upper() != "NULL":
        try:
            account_number_int = int(account_number_candidate)
        except Exception as e:
            account_number_int = None
        
        if account_number_int is not None:
            st.session_state["detected_account_number"] = account_number_int
            
            df_user = fetch_data("users")
            df_trans = fetch_data("transactions")
            df_grv = fetch_data("grievances")
            
            user_record = df_user[df_user["accountid"] == account_number_int]
            if not user_record.empty:
                first_name = user_record.iloc[0].get("firstname", "N/A")
                age = user_record.iloc[0].get("birthday", "N/A")
                education = user_record.iloc[0].get("Highest_educ_attained", "N/A")
                recommended_product = _ai_info_extractor(
                    f"Give me a product recommendation using Context-Aware Collaborative Filtering for customer {account_number_int}. Use the following data {df_user} and {df_trans}. Only tell the product, no other fillers"
                )
            else:
                first_name, age, education, recommended_product = "N/A", "N/A", "N/A", "N/A"
            
            trans_records = df_trans[df_trans["accountid"] == account_number_int].sort_values("transactiondate", ascending=False).head(3)
            grv_records = df_grv[(df_grv["accountid"] == account_number_int) & (df_grv["date"] > _get_time_1yrago())].sort_values("date", ascending=False).head(3)
            
            if not trans_records.empty:
                trans_str = "\n".join(trans_records.astype(str).tolist())
            else:
                trans_str = "No recent transactions."
            
            if not grv_records.empty:
                grv_str = "\n".join(grv_records.astype(str).tolist())
            else:
                grv_str = "No recent grievances."
            
            combined_str = f"Transactions:\n{trans_str}\n\nGrievances:\n{grv_str}"

            st.session_state["customer_info_data"] = {
                "first_name": first_name,
                "age": age,
                "education": education,
                "recommended_product": recommended_product,
                "combined_str": combined_str
            }
            
            st.sidebar.header("Extracted Customer Info")
            st.sidebar.text(f"Account Number: {account_number_int}")
            st.sidebar.text(f"First Name: {first_name}")
            st.sidebar.text(f"Birthday: {age}")
            st.sidebar.text(f"Highest Education: {education}")
            st.sidebar.text(f"Recommended Product: {recommended_product}")
            st.sidebar.text_area("Last 3 Transactions/Grievances", combined_str, height=120, key="transactions_area")

            
            st.session_state.customer_data_populated = True

# ---- Initialize Streamlit Session State ----

if 'in_call' not in st.session_state:
    st.session_state.in_call = False
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'ai_suggestion' not in st.session_state:
    st.session_state.ai_suggestion = ""
if 'customer_info' not in st.session_state:
    st.session_state.customer_info = "Customer info will appear here after the call ends."
if 'customer_data_populated' not in st.session_state:
    st.session_state.customer_data_populated = False

# ---- Layout ----

st.title("Osiris")

# AI helper suggestion (uneditable)
st.subheader("AI Helper Suggestion")
ai_suggestion_box = st.empty()
ai_suggestion_box.text_area("Suggestion", st.session_state.ai_suggestion, height=10, disabled=True, key="ai_suggestion_text_area")


# Sidebar: Always display customer info if detected; otherwise, show default placeholders
st.sidebar.header("Customer Information")

# Chat History (uneditable)
st.subheader("Chat History")
chat_history = st.empty()

def update_chat_history():
    """
    Display conversation
    """
    conversation_text = ""
    for msg in st.session_state.conversation:
        conversation_text += f"{msg['role']}: {msg['message']}\n"
    chat_history.text_area("Conversation", conversation_text, height=130, disabled=True)
    return conversation_text


conversation_text = update_chat_history()

def update_ai_suggestion():
    """
    display ai msg suggestions
    """
    if st.session_state.conversation:
        full_conv = ""
        for msg in st.session_state.conversation:
            full_conv += f"{msg['role']} Message: {msg['message']}\n"
        suggestion = _ai_agent(full_conv)
        st.session_state.ai_suggestion = suggestion
        ai_suggestion_box.text_area("Suggestion", suggestion, height=10, disabled=True)

# ---- Call Control Buttons ----

if not st.session_state.in_call:
    # When call is inactive, display the "Start Call" button centered in two columns.
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Call"):
            st.session_state.in_call = True
            st.session_state.conversation = []
            st.session_state.ai_suggestion = "Call started. AI helper will provide suggestions as the conversation unfolds."
            ai_suggestion_box.text_area("Suggestion", st.session_state.ai_suggestion, height=10, disabled=True)
            st.session_state.customer_data_populated = False
            if "customer_info_data" in st.session_state:
                del st.session_state["customer_info_data"]
    with col2:
        st.write("")  # Placeholder for alignment
else:
    # When call is active, display "End Call" and "Create Ticket" buttons side by side.
    col1, col2 = st.columns(2)
    with col1:
        if st.button("End Call"):
            st.session_state.in_call = False
            full_conv = ""
            for msg in st.session_state.conversation:
                full_conv += f"{msg['role']}: {msg['message']}\n"
            extracted = _ai_info_extractor(f"Summarize the concerns shown in the conversation and put in numbering: {full_conv}")
            st.session_state.customer_info = extracted
            st.sidebar.header("Extracted Customer Info")
            st.sidebar.text(extracted)
            st.success("Call ended.")
    with col2:
        if st.button("Create Ticket"):
            ticket_number = random.randint(1000, 9999)
            st.sidebar.header("Ticket Number")
            st.sidebar.text(f"Ticket #: {ticket_number}")

# ---- Message Input (only if call is active) ----

if st.session_state.in_call:
    st.subheader("New Message")
    with st.form(key="chat_form", clear_on_submit=True):
        # The radio selection for Customer/Agent is now horizontally aligned thanks to our custom CSS.
        sender = st.radio("Select Sender", ("Customer", "Agent"), key="sender_radio")
        message_input = st.text_input("Enter your message", key="message_input")
        submitted = st.form_submit_button("Send Message")
        if submitted:
            if message_input.strip() != "":
                st.session_state.conversation.append({"role": sender, "message": message_input})
                conversation_text = update_chat_history()
                update_ai_suggestion()
                check_and_update_customer_data()
            else:
                st.warning("Please enter a message before sending.")
