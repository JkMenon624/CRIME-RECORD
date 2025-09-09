# app_working.py - Main Streamlit app
import streamlit as st
from database import init_db, add_user, get_user_by_email, add_complaint, get_pending_complaints, register_case, get_all_laws, get_complaints_for_officer
from auth import verify_password, create_user
from severity_classifier import classify_severity
from pdf_generator import generate_case_pdf
from legal_database import seed_laws_if_empty
import os
from datetime import datetime

DB_PATH = "crime_records.db"

# Initialize DB & seed
init_db(DB_PATH)
seed_laws_if_empty(DB_PATH)

st.set_page_config(page_title="Crime Records Management", layout="wide")

st.markdown("<style> .header {font-size:28px; font-weight:700;} </style>", unsafe_allow_html=True)
st.markdown('<div class="header">Kerala Police — Crime Records Management (Prototype)</div>', unsafe_allow_html=True)
st.write("---")

# Simple navigation
tabs = st.tabs(["Home", "Lodge Complaint", "Police Login", "Legal DB"])

with tabs[0]:
    st.subheader("Welcome")
    st.write("""
    This is a prototype Crime Records Management System implemented with Streamlit + HTML/CSS + SQLite.
    Citizens can lodge complaints and police officers can review and register cases (PDFs).
    """)

with tabs[1]:
    st.subheader("Lodge Police Complaint (Citizen)")
    with st.form("complaint_form", clear_on_submit=True):
        c_name = st.text_input("Your full name", max_chars=120)
        c_email = st.text_input("Email (optional)")
        c_phone = st.text_input("Phone (optional)")
        c_title = st.text_input("Complaint title", max_chars=200)
        c_desc = st.text_area("Detailed description")
        # Let user suggest severity but we'll classify automatically as well
        c_severity_hint = st.selectbox("If you want, mark perceived severity", ["", "low", "medium", "high"])
        submitted = st.form_submit_button("Submit Complaint")
        if submitted:
            if not c_name or not c_title or not c_desc:
                st.error("Please fill name, title and description.")
            else:
                auto_sev = classify_severity(c_title + " " + c_desc)
                severity = c_severity_hint if c_severity_hint else auto_sev
                # add a citizen user placeholder (if email provided try to upsert)
                citizen_id = None
                if c_email:
                    user = get_user_by_email(DB_PATH, c_email)
                    if not user:
                        citizen_id = create_user(DB_PATH, name=c_name, email=c_email, password="")  # blank password citizen
                    else:
                        citizen_id = user["user_id"]
                # create complaint
                add_complaint(DB_PATH, user_id=citizen_id, title=c_title, description=c_desc, severity=severity)
                st.success(f"Complaint lodged successfully with severity = {severity.upper()}")

with tabs[2]:
    st.subheader("Police Officers — Login")
    police_email = st.text_input("Officer Email")
    police_password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Login"):
            user = get_user_by_email(DB_PATH, police_email)
            if not user or user["role"] != "police":
                st.error("No police account with that email. Create one using Register below (for demo).")
            else:
                if verify_password(police_password, user["password_hash"]):
                    st.success("Logged in successfully.")
                    st.session_state["police_user"] = user
                else:
                    st.error("Invalid credentials.")

    with col2:
        if st.button("Register demo police account"):
            # Demo register: password = "police123"
            if get_user_by_email(DB_PATH, police_email):
                st.info("Account already exists.")
            else:
                create_user(DB_PATH, name="Demo Officer", email=police_email or "officer@example.com", password="police123", role="police")
                st.success("Police account created (demo). Use password 'police123' to login.")

    # Police dashboard after login
    if "police_user" in st.session_state:
        st.write(f"Signed in as: {st.session_state['police_user']['name']} ({st.session_state['police_user']['email']})")
        st.write("---")
        st.subheader("Pending Complaints (sorted by severity & time)")
        complaints = get_pending_complaints(DB_PATH)
        # show table-like layout
        for comp in complaints:
            with st.expander(f"[{comp['severity'].upper()}] {comp['title']} — filed {comp['date_filed']}"):
                st.write(f"Description: {comp['description']}")
                st.write(f"Complainer ID: {comp['user_id']}")
                st.write("Actions:")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Register case #{comp['complaint_id']}", key=f"reg_{comp['complaint_id']}"):
                        # register case & create pdf
                        officer_id = st.session_state['police_user']['user_id']
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        pdf_path = generate_case_pdf(DB_PATH, comp, officer_name=st.session_state['police_user']['name'], out_folder="case_pdfs")
                        # register in DB
                        register_case(DB_PATH, complaint_id=comp['complaint_id'], police_officer_id=officer_id, pdf_path=pdf_path)
                        st.success(f"Registered case and PDF saved to: {pdf_path}")
                with col2:
                    st.write("Reference Laws (click to view)")
                    laws = get_all_laws(DB_PATH)
                    for law in laws[:6]:
                        st.markdown(f"- **{law['title']}**: {law['description'][:120]}...")

with tabs[3]:
    st.subheader("Legal Database (BNS & BNSS)")
    laws = get_all_laws(DB_PATH)
    q = st.text_input("Search law by keyword")
    filtered = []
    if q:
        qlow = q.lower()
        for law in laws:
            if qlow in law["title"].lower() or qlow in law["description"].lower() or qlow in law["category"].lower():
                filtered.append(law)
    else:
        filtered = laws
    st.write(f"Found {len(filtered)} entries")
    for law in filtered:
        st.markdown(f"**{law['title']}**  — *{law['category']}*")
        st.write(law["description"])
        st.write("---")
