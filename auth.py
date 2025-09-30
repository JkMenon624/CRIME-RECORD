# auth.py - Authentication and Registration
import streamlit as st
from database import Database
import hashlib

# Initialize database instance
db = Database()

# ---------- Helper: Hash Password ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ---------- Login ----------
def login_form():
    """Display login form"""
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if email and password:
                user = db.authenticate_user(email, hash_password(password))
                if user:
                    st.session_state.user = user
                    st.success(f"Welcome, {user['name']} ({user['role'].title()}) 🎉")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
            else:
                st.error("⚠️ Please fill in all fields")

# ---------- Registration ----------
def register_form():
    """Display registration form for citizens"""
    st.subheader("📝 Citizen Registration")
    
    with st.form("register_form"):
        name = st.text_input("Full Name", placeholder="Enter your full name")
        email = st.text_input("Email", placeholder="Enter your email")
        phone = st.text_input("Phone", placeholder="Enter your phone number")
        district = st.text_input("District", placeholder="Enter your district")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        submitted = st.form_submit_button("Register", use_container_width=True)
        
        if submitted:
            if all([name, email, phone, district, password, confirm_password]):
                if password == confirm_password:
                    user_id = db.create_user(
                        name, email, phone, hash_password(password), role="citizen", district=district
                    )
                    if user_id:
                        st.success("✅ Registration successful! Please login.")
                        st.rerun()
                    else:
                        st.error("⚠️ Email already exists")
                else:
                    st.error("⚠️ Passwords do not match")
            else:
                st.error("⚠️ Please fill in all fields")

# ---------- Logout ----------
def logout():
    """Logout user"""
    if 'user' in st.session_state:
        del st.session_state.user
    st.rerun()

# ---------- Require Auth ----------
def require_auth(role=None):
    """Require authentication"""
    if 'user' not in st.session_state:
        st.error("🚫 Please log in to continue.")
        st.stop()
    
    if role and st.session_state.user['role'] != role:
        st.error("🚫 Access denied. This section is only for " + role.title())
        st.stop()

# ---------- Get Current User ----------
def get_current_user():
    """Get current logged in user"""
    return st.session_state.get('user', None)
