import streamlit as st
from supabase import create_client

st.title("Supabase connection test")

try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

    supabase = create_client(supabase_url, supabase_key)

    response = supabase.table("categories").select("*").limit(10).execute()

    st.success("Подключение к Supabase работает ✅")
    st.write("Первые категории из базы:")
    st.dataframe(response.data)

except Exception as error:
    st.error("Ошибка подключения к Supabase")
    st.exception(error)
