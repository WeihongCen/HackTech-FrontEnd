# app.py
import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from chat import database_agent

st.set_page_config(layout="wide")
with st.sidebar:
    # =========================================================================================
    # DATABASE VIEWER
    # =========================================================================================
    st.header("📊 Database Viewer")

    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    tables = ["material_master", 
              "stock_levels",
              "stock_movements",
              "dispatch_parameters", 
              "material_orders", 
              "sales_orders", 
              "suppliers",
              "specs",
              ]

    selected_table = st.selectbox("Choose a table", tables)

    if selected_table:
        try:
            response = supabase.table(selected_table).select("*").limit(100).execute()
            if response.data:
                df = pd.DataFrame(response.data)
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
        type=["pdf", "csv", "txt", "eml"]
    )

    if uploaded_files:
        if st.button("Upload"):
            files = [('files', (file.name, file.getvalue())) for file in uploaded_files]
            response = requests.post("http://localhost:5000/upload", files=files)

            if response.status_code == 200:
                st.success("Files uploaded successfully!")
            else:
                st.error(f"Upload failed: {response.text}")

# =========================================================================================
# Chat
# =========================================================================================
st.header("🤖 Hugo")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask Hugo about your data."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        # response = st.write_stream(database_agent(prompt))
        response = st.markdown(database_agent(prompt))
    st.session_state.messages.append({"role": "assistant", "content": response})