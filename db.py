import streamlit as st
from supabase import create_client

def has_supabase_config() -> bool:
    return bool(st.secrets.get("SUPABASE_URL")) and bool(st.secrets.get("SUPABASE_KEY"))

@st.cache_resource(show_spinner=False)
def get_supabase():
    if not has_supabase_config():
        return None
    return create_client(
        st.secrets["SUPABASE_URL"].strip(),
        st.secrets["SUPABASE_KEY"].strip()
    )

supabase = get_supabase()
