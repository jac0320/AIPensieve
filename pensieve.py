import streamlit as st
import logging
import os
import json
import uuid

from faker import Faker
import google.generativeai as genai

from extract import extract
from entering import choose_emoji, retrieve_decision, embed_fn, vectorstore
from synthetic import random_self_intro
from utils import *
from display import display_entry

from constants import (
    DEFAULT_LOCAL_VECTOR_STORE, 
    GEMINI_API_KEY, 
    PREDEFINED_SELF_INTRODUCTION
)

st.set_page_config(page_title="Pensieve", page_icon="🧙", layout="centered", initial_sidebar_state="collapsed")

import sys
if sys.platform.startswith("linux"):
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

logging.basicConfig(level=logging.INFO)


def reset_chat(self_intro):
    st.session_state.chat_history = []
    model = genai.GenerativeModel('gemini-pro')
    st.session_state.chat_session = model.start_chat(history=[
        {
            "role": "user",
            "parts": [f"Info about me: {self_intro}. You are a helpful person that serves like Pensieve for me. You have access to my diary/journal and can help me/other remember things about me. You only know things about me based on my writings and no other prior knowledge. You are a strong Pensieve and can help me/other people recreate vivid memories like we are reliving them."]
        },
        {
            "role": "model",
            "parts": ["Sure. I will do it."]
        }
    ])


def main():

    st.title('Pensieve 🧙‍♂️')

    user_category = st.selectbox(label="User", options=['Site', 'Alex', 'Random', 'You'], index=0)

    if user_category.lower() in PREDEFINED_SELF_INTRODUCTION:
        user = user_category
    elif user_category.lower() == 'random':
        if 'user' in st.session_state:
            if st.session_state['user'] in ['Site', 'Alex']:
                user = Faker().name().split(' ')[0]
            else:
                user = st.session_state['user']
        else:
            user = Faker().name().split(' ')[0]
    else:
        user = st.text_input("Your Name", value="")
        if user == "":
            st.warning("Please enter your name.")
            return

    st.session_state['user'] = user

    if user_category.lower() in PREDEFINED_SELF_INTRODUCTION:
        self_intro = st.text_area("Self Introduction", value=PREDEFINED_SELF_INTRODUCTION[user.lower()])
    elif user_category.lower() == 'random':
        self_intro = st.text_area("Self Introduction", value=random_self_intro(user))
    else:
        self_intro = st.text_area("Self Introduction", value="")

    if 'session_id' not in st.session_state:
        session_id = uuid.uuid4().hex
        st.session_state['session_id'] = session_id
        st.session_state.logger = logging.getLogger(session_id)
        st.session_state.logger.setLevel(logging.INFO)

    if 'chat_session' not in st.session_state:  # this is used for the chat session (system context and retrieval information will be here)
        reset_chat(self_intro)
    
    if 'chat_history' not in st.session_state:  # this is used for displaying the chat history
        st.session_state.chat_history = []
    
    if 'gemini_client' not in st.session_state:
        st.session_state.gemini_client = genai.configure(api_key=GEMINI_API_KEY)

    st.sidebar.button("Clear Chat History", on_click=reset_chat, args=(self_intro,), use_container_width=True)
        

    extract_tab, entering_tab = st.tabs(
        ["Extract 🪄", "Entering 🔮"]
    )

    with extract_tab:

        uploaded_file = st.file_uploader("Extract your memory here", type=['png', 'jpg', 'jpeg'])
        uploaded_text = st.text_area("Enter your memory here", value=None)

        if uploaded_file is not None:
            st.image(uploaded_file)

        if uploaded_text is not None or uploaded_file is not None:
            if st.button("Extract 🪄💆‍♀️", type="primary", use_container_width=True):
                entry = extract(self_intro, uploaded_file, uploaded_text)
                if uploaded_file is None:
                    display_entry(entry, show_media=False, show_full=True)
                else:
                    display_entry(entry)
            

    with entering_tab:

        journals = vectorstore(user)
        if journals is None:
            st.warning("🫙 No memories found for entering.")
            return
        
        client = chromadb.PersistentClient(DEFAULT_LOCAL_VECTOR_STORE)
        collection = client.get_collection(name=user)

        for msg in st.session_state.chat_history:
            with st.chat_message(msg['role'], avatar=msg['avatar'] if 'avatar' in msg else '🧙‍♂️'):
                st.write(msg['content'])
        
        if query := st.chat_input("Query"):
            st.session_state.logger.info(f"Session {st.session_state.session_id} | Query: {query}")
            emoji = choose_emoji(query)
            st.session_state.chat_history.append({"role": "user", 'avatar': emoji, "content": query})
            with st.chat_message("user", avatar=emoji):
                st.write(query)

            # try to see if the conversation requires more information
            if retrieve_decision(query) or len(st.session_state.chat_history) == 1:  
                query_embedding = embed_fn(title="", text=query, task_type="retrieval_query")
                results = collection.query(query_embedding, n_results=2)
                prompt = ""
                for i in range(len(results['ids'][0])):
                    prompt += f"Given the journals below: {results['documents'][0][i]} \n {str(results['metadatas'][0][i])} \n\n"
                prompt += f"Responde to {query} through describing a vivid memory based on the above information."
            else:
                prompt = query
            
            st.session_state.logger.info(f"Session {st.session_state.session_id} | Prompt: {prompt}")

            response = st.session_state.chat_session.send_message(prompt)
            st.session_state.chat_history.append({"role": "model", "content": response.text})
            with st.chat_message("model", avatar="🧙‍♂️"):
                st.write_stream(stream_data(response.text))
            
            st.session_state.logger.info(f"Session {st.session_state.session_id} | Response: {response.text}")
            
            st.rerun()


if __name__ == '__main__':
    main()