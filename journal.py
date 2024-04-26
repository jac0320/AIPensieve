import streamlit as st
import os
import pandas as pd
import json
import google.generativeai as genai
import google.ai.generativelanguage as glm
import chromadb

__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')


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
    
    metadatas = []
    for _, v in journals.items():
        metadatas.append({k: v for k,v in v['weather_data'].items() if isinstance(v, str) or isinstance(v, int) or isinstance(v, float) or isinstance(v, bool)})
    
    if collection.count() == 0:
        collection.add(
            documents=[v['journal'] for _, v in journals.items()],
            embeddings=[embed_fn(title=v['title'], text=v['journal']) for _, v in journals.items()],
            metadatas=metadatas,
            ids=[k for k, _ in journals.items()]
        )
    

def main():

    st.title('Journal')

    user = st.selectbox(label="User", options=['Site', 'Long'], index=0)
    vectorstore(user)

    client = chromadb.PersistentClient(DEFAULT_LOCAL_VECTOR_STORE)
    collection = client.get_collection(name=user)

    if query := st.chat_input("Query"):
        query_embedding = embed_fn(title="", text=query, task_type="retrieval_query")
        results = collection.query(query_embedding, n_results=2)
        for i in range(len(results['ids'])):
            st.write(results['ids'][0][i])
            st.write(results['metadatas'][0][i])
            st.write(results['documents'][0][i])
        st.write('---')


if __name__ == '__main__':
    main()