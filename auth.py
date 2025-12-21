import streamlit as st
import os

def admin_login():
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    with st.sidebar:
        if st.session_state.is_admin:
            with st.container(border=True):
                st.markdown("### 🔐 Admin Area")
                st.success("🟢 Admin mode enabled")

                if st.button("Logout"):
                    st.session_state.is_admin = False
                    st.rerun()

        else:
            with st.form("admin_login_form"):
                st.markdown("### 🔐 Admin Area")
                password = st.text_input(
                    "Admin password",
                    type="password"
                )
                submitted = st.form_submit_button("Login")

            if submitted:
                if password == st.secrets["admin"]["password"]:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Incorrect password")