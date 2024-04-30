import streamlit as st
import logging
import os
import json
import uuid

import pandas as pd
import google.generativeai as genai

from extract import extract
from synthetic import random_self_intro
from utils import *
from display import display_entry
from constants import (
    DEFAULT_EMBEDDING_MODEL, 
    DEFAULT_LOCAL_VECTOR_STORE, 
    GEMINI_API_KEY, 
    PREDEFINED_SELF_INTRODUCTION
)


import sys
if sys.platform.startswith("linux"):
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb

logging.basicConfig(level=logging.INFO)



def embed_fn(title, text, task_type="retrieval_document"):
    return st.session_state.gemini_client.embed_content(
        model=DEFAULT_EMBEDDING_MODEL,
        content=text,
        task_type=task_type,
        title=title
    )["embedding"]


def vectorstore(name):

    client = chromadb.PersistentClient(DEFAULT_LOCAL_VECTOR_STORE)
    
    with open(f"converted_data/{name.lower()}_journal.json", "r") as f:
        journals = json.load(f)

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
                    title=v['title'],
                    text=v['journal'] + str(v.get('music', '')) + str(v['location_data']) + str(v['weather_data']),
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



def main():

    st.title('Pensieve 🧙‍♂️')

    if 'session_id' not in st.session_state:
        session_id = uuid.uuid4().hex
        st.session_state['session_id'] = session_id
        st.session_state.logger = logging.getLogger(session_id)
        st.session_state.logger.setLevel(logging.INFO)

    if 'chat_session' not in st.session_state:
        st.session_state.chat_session = []
    
    if 'gemini_client' not in st.session_state:
        st.session_state.gemini_client = genai.configure(api_key=GEMINI_API_KEY)

    user = st.selectbox(label="User", options=['Site', 'Long', 'Random', 'You'], index=0)

    if user.lower() in PREDEFINED_SELF_INTRODUCTION:
        self_intro = st.text_area("Self Introduction", value=PREDEFINED_SELF_INTRODUCTION[user.lower()])
    elif user.lower() == 'random':
        self_intro = st.text_area("Self Introduction", value=random_self_intro())
    else:
        self_intro = st.text_area("Self Introduction", value="")

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
        
        st.info("Under Construction 🚧")
        assert True
        # journals = vectorstore(user)

        # client = chromadb.PersistentClient(DEFAULT_LOCAL_VECTOR_STORE)
        # collection = client.get_collection(name=user)
        # if query := st.chat_input("Query"):
        #     query_embedding = embed_fn(title="", text=query, task_type="retrieval_query")
        #     results = collection.query(query_embedding, n_results=2)


if __name__ == '__main__':
    main()