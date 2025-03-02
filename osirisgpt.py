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


def _agent_advisor():
    cust_agent = 0
    running_msg = ["Hi. This is DITO Agent. How may I help you?"]
    call_log = {}
    msg_info = {"account number":'NULL',
                "rating":'NULL'}
    print(f"Agent Message: {'\n'.join(running_msg)}")

    # get data from sql
    df_user = fetch_data("users")
    df_trans = fetch_data("transactions")
    df_grv =fetch_data("grievances")
    
    while True:
        # customers turn to message
        if cust_agent == 0:
            user_input = _get_message("Customer")#input("Customer Message:")

            cust_mcnt = len([_ for _ in call_log.keys() if "Customer Message" in _])

            call_log[f"Customer Message{cust_mcnt}"] = {"role": "user", "content": user_input}
            running_msg.append(f"Customer Message: {user_input}")
            # toggle to agent's turn
            cust_agent = 1
    
            # exit chat
            if user_input == "exit":
                print("Chat ended")
                msg_info["rating"] == _extract_info(call_log, info="rating")
                break
            else:
                msg = _ai_agent("\n".join(running_msg))
                print("\nAI advisor:\n",msg,"\n")
        
        # agents turn to message
        else:
            user_input = _get_message("Agent")#input("Agent Message:")
    
            # register conversation
            agent_mcnt = len([_ for _ in call_log.keys() if "Agent Message" in _])
            
            call_log[f"Agent Message{cust_mcnt}"] = {"role": "assistant", "content": user_input}
            running_msg.append(f"Agent Message: {user_input}")
            # toggle to customer's turn
            cust_agent = 0

            # exit chat
            if user_input == "exit":
                print("Chat ended")
                msg_info["rating"] == _extract_info(call_log, info="rating")
                break


        # Check if there are information shared already
        if ("account number" in "\n ".join(running_msg) or "customer number" in "\n ".join(running_msg)) and (msg_info["account number"]=='NULL'):
            #print("*******CHECKING******")
            msg_info["account number"] = _extract_info(call_log, info="account number")
        if ("rate" in "\n ".join(running_msg) or "rating" in "\n ".join(running_msg)) and (msg_info["rating"]=='NULL'):
            #print("*******Rating******")
            msg_info["rating"] = _extract_info(call_log, info="rating")
        
    
    return (call_log, msg_info, df_user[df_user["accountid"]==float(msg_info['account number'])],
            df_trans[df_trans["accountid"]==msg_info['account number']].sort_values("transactiondate",ascending=False).head(3),
            df_grv[(df_grv["accountid"]==msg_info['account number']) &
                     (df_grv["date"]>_get_time_1yrago())].sort_values("date",ascending=False).head(3))
