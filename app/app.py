# app.py
import streamlit as st
import pandas as pd
import requests
from supabase import create_client
import asyncio
from typing import AsyncGenerator
from dotenv import load_dotenv
import os
load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SERVER_URL = os.getenv("SERVER_URL")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLES = ["material_master", 
          "stock_levels",
          "stock_movements",
          "dispatch_parameters", 
          "material_orders", 
          "sales_orders", 
          "suppliers",
          "specs",
          ]


def call_flask_query(user_input: str) -> str:
    try:
        response = requests.post(
            f"{SERVER_URL}/query",
            json={"user_input": user_input},
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return str(data.get("response"))
        else:
            return f"Error: {data.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Request failed: {str(e)}"
    

def to_sync_generator(async_gen: AsyncGenerator):
    while True:
        try:
            yield asyncio.run(anext(async_gen))
        except StopAsyncIteration:
            break


st.set_page_config(layout="wide")
with st.sidebar:
    # =========================================================================================
    # DATABASE VIEWER
    # =========================================================================================
    st.header("📊 Database Viewer")

    selected_table = st.selectbox("Choose a table", TABLES)

    if selected_table:
        try:
            table_response = supabase.table(selected_table).select("*").execute()
            if table_response.data:
                df = pd.DataFrame(table_response.data)
                st.dataframe(df)
            else:
                st.info(f"No data in table {selected_table}.")
        except Exception as e:
            st.error(f"Cannot find table")

    # =========================================================================================
    # DATABASE UPLOAD
    # =========================================================================================        
    st.header("📁 File Uploader")

    uploaded_files = st.file_uploader(
        "Upload files to automatically populate the database", 
        accept_multiple_files=True,
        type=["csv", "txt", "eml"]
    )

    if uploaded_files:
        if st.button("Upload"):
            files = [('files', (file.name, file.getvalue())) for file in uploaded_files]
            file_response = requests.post(f"{SERVER_URL}/upload", files=files)

            if file_response.status_code == 200:
                st.success("Files uploaded successfully!")
            else:
                st.error(f"Upload failed: {file_response.text}")

# =========================================================================================
# Chat
# =========================================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "preset_prompt" not in st.session_state:
    st.session_state.preset_prompt = ""

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if len(st.session_state.messages) == 0:
    suggested_prompts = [
        "Which parts are low in stock?",
        "Who is my most reliable supplier?",
        "How many Voltway S1 V1 Standard can we produce?",
    ]

    with st.container():
        for i, suggestion in enumerate(suggested_prompts):
            if st.button(suggestion, key=suggestion):
                st.session_state.preset_prompt = suggestion

user_prompt = st.chat_input("Ask Hugo about your data.")
if user_prompt or st.session_state.preset_prompt:
    prompt = user_prompt or st.session_state.preset_prompt
    st.session_state.preset_prompt = ""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        placeholder = st.empty()

        async def animate_loading():
            dots = ["", ".", "..", "..."]
            i = 0
            while not st.session_state.get("response_ready", False):
                placeholder.markdown(f"Hugo is thinking{dots[i % 4]}")
                i += 1
                await asyncio.sleep(0.2)

        async def wait_hugo():
            loading_task = asyncio.create_task(animate_loading())
            server_response = call_flask_query(prompt)
            st.session_state["response_ready"] = True
            await loading_task
            placeholder.markdown(server_response)
            st.session_state.messages.append({"role": "assistant", "content": server_response})

        st.session_state["response_ready"] = False
        asyncio.run(wait_hugo())