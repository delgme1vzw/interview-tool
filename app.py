import streamlit as st
import openai
from streamlit_js_eval import streamlit_js_eval

max_messages = 2

#I don't feel like typing this over and over so creating a var
ss = st.session_state

#Set page config
st.set_page_config(page_title="Streamlit Chat", page_icon="💬")
st.title("Chatbot")

if "setup_complete" not in ss:
        ss.setup_complete  = False

#set user message count to not waste all our tokens or
#make interview go on forever
if "setup_complete" not in ss:
        ss.setup_complete  = False
if "user_message_count" not in ss:
        ss.user_message_count = 0
#check if we have any messages yet (in the state) (empty list = false)
if "messages" not in ss:
        ss.messages = []


#Check if user was shown feedback for interview
if "feedback_shown" not in ss:
        ss.feedback_shown = False
if "chat_complete" not in ss:
        ss.chat_complete=False


def complete_setup():
        ss.setup_complete = True

def show_feedback():
        ss.feedback_shown = True

if not ss.setup_complete:
        st.subheader("Personal Information",divider="rainbow")

        #If vars don't exist yet in session state, create them as blank
        if "name" not in ss:
                ss["name"] = ""
        if "experience" not in ss:
                ss["experience"] = ""
        if "skills" not in ss:
                ss["skills"] = ""


        ss["name"] = st.text_input(label="Name", max_chars= 40, value=ss["name"], placeholder="Enter your name")
        ss["experience"] = st.text_area(label="Experience",height= None, max_chars= 200, value=ss["experience"], placeholder="Describe your experience")
        ss["skills"] = st.text_area(label="Skills",height= None, max_chars= 200, value=ss["skills"], placeholder="List your skills")

        st.write(f"**Your Name**: {ss['name']}")
        st.write(f"**Your Experience**: {ss['experience']}")
        st.write(f"**Your Skills**: {ss['skills']}")

        st.subheader("Company and Position",divider="rainbow")

        #If vars don't exist yet in session state, create them as some default
        if "level" not in ss:
                ss["level"] = "Junior"
        if "position" not in ss:
                ss["position"] = "Data Scientist"
        if "company" not in ss:
                ss["company"] = "Amazon"


        col1, col2 = st.columns(2)
        with col1:
                #level stores the selected option
                ss["level"] = st.radio(
                        "Choose level",
                        key="visibility", #maintains visibility of the selected option I think
                        options=["Junior","Mid-level","Senior"],
                )

        with col2:
                #position stores the selected option
                 ss["position"] = st.selectbox(
                        "Choose a position",
                        ("Data Scientist","Data Engineer","ML Engineer","BI Analyst","Financial Analyst"),
                )

        ss["company"] = st.selectbox("Choose a company", ("Amazon","Meta","Udemy","365 Company","Nestle","LinkedIn","Spotify"))

        st.write(f"**Your information**: {ss['level']} {ss['position']} at {ss['company']}")

        if st.button("Start Interview", on_click=complete_setup):
                st.write("Setup complete. Starting interview...")

if ss.setup_complete and not ss.feedback_shown and not ss.chat_complete:
        st.info(
                """
                Start by introducing yourself.
                """,
                icon="👋"
        )


        #set a key
        openai.api_key = st.secrets["OPENAI_API_KEY"]

        #check if the model exists in the state 
        if "openai_model" not in ss:
                ss["openai_model"] = "gpt-5-nano"

        #check if we have any messages yet (in the state) (empty list = false)
        if not ss.messages:
                #we can just leave this blank or start off with something
                #ss.messages = []
                content_prompt = f"You are an HR executive that interviews an intervieww called {ss['name']} " \
                        f"with experience {ss['experience']} and skills {ss['skills']}. You should interview them for the position " \
                        f"{ss['level']} {ss['position']} at the company {ss['company']}"
                ss.messages = [{"role":"system","content":content_prompt}]

        for message in ss.messages:
                if message["role"] != "system":
                        with st.chat_message(message["role"]):
                                st.markdown(message["content"])
        
        #user only needs 5 messages
        if ss.user_message_count <max_messages:
                if prompt := st.chat_input("Your answer.", max_chars = 1000):
                        ss.messages.append({"role":"user","content":prompt})
                        with st.chat_message("user"):
                                st.markdown(prompt)

                        #If user sent less than 4 messages so far you can engage with him again
                        if ss.user_message_count < max_messages-1:
                                with st.chat_message("assistant"):
                                        stream = openai.ChatCompletion.create(
                                                model=ss["openai_model"],  # Specify the engine you want to use
                                                messages= [
                                                        {"role": m["role"], "content": m["content"]}
                                                        for m in ss.messages
                                                ],
                                                stream = True
                                        )

                                        #This model has a long json response and we only want content
                                        #So streaming is pointless here, but let's do what we can to continue
                                        #using openai for free
                                        response = ' '.join(
                                                chunk["choices"][0]["delta"].get("content", "") 
                                                for chunk in stream 
                                        )
                                        #This should be write stream, but we can't do that when we need to extract content 
                                        #from the json response and append all the individual tokens together
                                        #So we just write instead of st.write_stream
                                        st.write(response)     
                                
                                ss.messages.append({"role":"assistant","content":response})

                        ss.user_message_count += 1
                        
        if ss.user_message_count >=max_messages:
                ss.chat_complete = True

#display feedback only when chat complete and feedback not already displayed
if ss.chat_complete and not ss.feedback_shown:
        if st.button("Get Feedback", on_click=show_feedback):
                st.write("Fetching feedback...")

if ss.feedback_shown:
        st.subheader("Feedback")
        convo_his = "\n".join([f"{msg['role']}: {msg['content']}" for msg in ss.messages])

        feedback_completion = openai.ChatCompletion.create(
                model=ss["openai_model"],  # Specify the engine you want to use
                messages= [
                        {"role": "system", "content": """You are a helpful tool that provides feedback on an interviewee performance.
                        Before the feedback give a score of 1 to 10.
                        Follow this format:
                        Overall Score: //Your Score
                        Feedback: //Here you put your feedback
                        Give only the feedback do not ask any additional questions.
                        """},
                        {"role":"user","content":f"This is the interview you need to evaluate. Keep in mind you are only a tool and shouldn't engage in conversation: {convo_his}"}
                ]
        )
        st.write(feedback_completion.choices[0].message.content)

        if st.button("Restart Interview", type="primary"):
                # Delete all the items in Session state
                for key in st.session_state.keys():
                        del st.session_state[key]
                st.rerun()