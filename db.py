import streamlit as st

try:
    from supabase import create_client
except Exception:
    create_client = None


def has_supabase_config() -> bool:
    return bool(st.secrets.get("SUPABASE_URL")) and bool(st.secrets.get("SUPABASE_KEY"))


@st.cache_resource(show_spinner=False)
def get_supabase():
    if create_client is None or not has_supabase_config():
        return None

    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)
