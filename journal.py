import streamlit as st
import os
import pandas as pd
import json
import google.generativeai as genai
import google.ai.generativelanguage as glm

import sys
if sys.platform.startswith("linux"):
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import chromadb


DEFAULT_LOCAL_VECTOR_STORE = 'localvs'
DEFAULT_EMBEDDING_MODEL = 'models/embedding-001'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


def embed_fn(title, text, task_type="retrieval_document"):
  return genai.embed_content(model=DEFAULT_EMBEDDING_MODEL,
                             content=text,
                             task_type=task_type,
                             title=title)["embedding"]

def vectorstore(name):

    genai.configure(api_key=GEMINI_API_KEY)

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

    st.title('Journal')

    user = st.selectbox(label="User", options=['Site', 'Long'], index=0)
    journals = vectorstore(user)

    client = chromadb.PersistentClient(DEFAULT_LOCAL_VECTOR_STORE)
    collection = client.get_collection(name=user)

    if query := st.chat_input("Query"):
        query_embedding = embed_fn(title="", text=query, task_type="retrieval_query")
        results = collection.query(query_embedding, n_results=2)
        for i in range(len(results['ids'])):
            journal_key = results['ids'][0][i]
            if 'media' in journal_key:
                st.image(journal_key)
            with st.expander("Moment Music"):
                st.write(journals[journal_key].get('music', {}))
            with st.expander("Moment Weather"):
                st.write(journals[journal_key].get('weather_data', {}))
            with st.expander("Moment Location"):
                st.write(journals[journal_key].get('location_data', {}))
            with st.expander("Moment Metadata"):
                st.write(journals[journal_key].get('metadata_data', {}))
            st.write(results['documents'][0][i])
        st.write('---')


if __name__ == '__main__':
    main()