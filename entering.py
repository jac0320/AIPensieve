import streamlit as st
import google.generativeai as genai
import emoji
import json

from constants import DEFAULT_EMBEDDING_MODEL, DEFAULT_LOCAL_VECTOR_STORE

import sys
if sys.platform.startswith("linux"):
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

def embed_fn(title, text, task_type="retrieval_document"):

    return genai.embed_content(
        model=DEFAULT_EMBEDDING_MODEL,
        content=text,
        task_type=task_type,
        title=title
    )["embedding"]


def vectorstore(name):

    client = chromadb.PersistentClient(DEFAULT_LOCAL_VECTOR_STORE)
    
    try:
        with open(f"converted_data/{name.lower()}_journal.json", "r") as f:
            journals = json.load(f)
    except FileNotFoundError:
        st.session_state.logger.warn(f"Failed to load journal data for {name}")
        return

    st.info(f"Found {len(journals)} journal entries for {name}.")

    try:
        collection = client.get_collection(name=name)
    except ValueError:
        collection = client.create_collection(name=name)
    

    if collection.count() == 0:
        metadatas = []
        embedding_content = []
        for _, v in journals.items():
            metadatas.append(
                {k: v for k,v in v['weather_data'].items() if isinstance(v, str) or isinstance(v, int) or isinstance(v, float) or isinstance(v, bool)}
            )
            embedding_content.append(
                embed_fn(
                    title=v.get('title', v.get('journal_title', '')),
                    text=v['journal'] + str(v.get('music', '')) + str(v.get('location_data', '')) + str(v.get('weather_data', '')) + str(v.get('utc_dt', '')) + str(v.get('mood_data', '')) + str(v.get('metadata', '')) + str(v.get('journal_title', '')) + str(v.get('user_journal', '')),
                    task_type='retrieval_document'
                )
            ) 
        collection.add(
            documents=[v['journal'] for _, v in journals.items()],
            embeddings=embedding_content,
            metadatas=metadatas,
            ids=[k for k, _ in journals.items()]
        )
    
    return journals

def extract_chat_history() -> str:
    chat_history = ""
    for msg in st.session_state.chat_session.history:
        chat_history += f"{msg.role}: {msg.parts[0].text}\n"
    return chat_history 


def choose_emoji(query):
    
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""Generate an emoji that best describe message: {query}"""
    response = model.generate_content(prompt)
    emojis = [char for char in response.text if emoji.is_emoji(char)]
    if len(emojis) == 0:
        return "🙂"
    return emojis[0]


def retrieve_decision(query):
    
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    We are currently in a conversation where we trying to probe into one my's memory.
    Here is the conversation so far:
    {extract_chat_history()}

    One says: {query}

    Based on the conversation, do you think we already have enough context to response to?
    Answer in json format with key 'decision' and value 'yes' or 'no'.
    """
    st.session_state.logger.info(f"Session {st.session_state.session_id} | Retrieve Decision Prompt: {prompt}")
    response = model.generate_content(prompt)
    st.session_state.logger.info(f"Session {st.session_state.session_id} | Retrieve Decision Response: {response.text}")
    return ('no' in response.text.lower()) or ('false' in response.text.lower())
