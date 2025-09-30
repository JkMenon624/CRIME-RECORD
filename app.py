import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import hashlib
import uuid
import os

# Import custom modules
from database import Database
from auth import login_form, register_form, logout, require_auth, get_current_user, hash_password
from legal_database import display_legal_database
from severity_classifier import classify_severity, get_severity_badge, get_severity_color
from pdf_generator import generate_case_pdf

# Initialize database
db = Database()
db.init_db()

# Page configuration
st.set_page_config(
    page_title="Crime Records Management System",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Emergency warning banner
st.error("⚠️ **EMERGENCY WARNING**: This system is not for emergency complaints. For emergencies, please call your local emergency numbers (100 for Police, 101 for Fire, 102 for Ambulance).")

def init_session_state():
    """Initialize session state variables"""
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'
    if 'user' not in st.session_state:
        st.session_state.user = None

def sidebar_navigation():
    """Create sidebar navigation"""
    st.sidebar.title("🚨 Crime Records System")
    
    # Current user info
    current_user = get_current_user()
    if current_user:
        st.sidebar.success(f"👤 {current_user['name']}")
        st.sidebar.write(f"**Role:** {current_user['role'].title()}")
        if current_user['role'] == 'police':
            st.sidebar.write(f"**Badge:** {current_user.get('badge_number', 'N/A')}")
        st.sidebar.write("---")
    
    # Navigation menu
    menu_options = ["📊 Crime Dashboard", "🔐 Login/Register"]
    
    if current_user:
        if current_user['role'] == 'citizen':
            menu_options.extend([
                "📝 Submit Complaint",
                "📋 My Complaints",
                "⚖️ Legal Database"
            ])
        elif current_user['role'] == 'police':
            menu_options.extend([
                "👮 Officer Dashboard",
                "📂 Pending Complaints", 
                "🔍 Search All Complaints",
                "📄 Case Management",
                "📊 Analytics Dashboard",
                "⚖️ Legal Database"
            ])
        menu_options.append("🚪 Logout")
    
    selected = st.sidebar.radio("Navigation", menu_options)
    
    # Map selection to page
    page_mapping = {
        "📊 Crime Dashboard": "dashboard",
        "🔐 Login/Register": "login",
        "📝 Submit Complaint": "submit_complaint",
        "📋 My Complaints": "my_complaints",
        "👮 Officer Dashboard": "officer_dashboard",
        "📂 Pending Complaints": "pending_complaints",
        "🔍 Search All Complaints": "search_complaints",
        "📄 Case Management": "case_management",
        "📊 Analytics Dashboard": "analytics",
        "⚖️ Legal Database": "legal_database",
        "🚪 Logout": "logout"
    }
    
    return page_mapping.get(selected, "dashboard")

def crime_dashboard():
    """Display crime statistics dashboard"""
    st.title("📊 Crime Statistics Dashboard")
    st.subheader("Kerala State Crime Analytics")
    
    # Get crime statistics
    conn = db.connect()
    
    # Overall statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_complaints = pd.read_sql_query("SELECT COUNT(*) as count FROM Complaints", conn).iloc[0]['count']
        st.metric("Total Complaints", total_complaints)
    
    with col2:
        resolved_complaints = pd.read_sql_query("SELECT COUNT(*) as count FROM Complaints WHERE status = 'Resolved'", conn).iloc[0]['count']
        resolution_rate = (resolved_complaints / total_complaints * 100) if total_complaints > 0 else 0
        st.metric("Resolution Rate", f"{resolution_rate:.1f}%")
    
    with col3:
        pending_complaints = pd.read_sql_query("SELECT COUNT(*) as count FROM Complaints WHERE status = 'Pending'", conn).iloc[0]['count']
        st.metric("Pending Cases", pending_complaints)
    
    with col4:
        fir_cases = pd.read_sql_query("SELECT COUNT(*) as count FROM Cases", conn).iloc[0]['count']
        fir_rate = (fir_cases / total_complaints * 100) if total_complaints > 0 else 0
        st.metric("FIR Conversion Rate", f"{fir_rate:.1f}%")
    
    st.write("---")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Complaint Trends")
        
        # Complaints over time
        complaints_trend = pd.read_sql_query("""
            SELECT DATE(date_filed) as date, COUNT(*) as count 
            FROM Complaints 
            WHERE date_filed >= date('now', '-30 days')
            GROUP BY DATE(date_filed)
            ORDER BY date
        """, conn)
        
        if not complaints_trend.empty:
            fig_trend = px.line(complaints_trend, x='date', y='count', 
                              title="Complaints Over Last 30 Days",
                              markers=True)
            fig_trend.update_layout(xaxis_title="Date", yaxis_title="Number of Complaints")
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No complaint data available for the last 30 days")
    
    with col2:
        st.subheader("📊 Crime Categories")
        
        # Crime type distribution
        crime_types = pd.read_sql_query("""
            SELECT crime_type, COUNT(*) as count 
            FROM Complaints 
            GROUP BY crime_type 
            ORDER BY count DESC
            LIMIT 10
        """, conn)
        
        if not crime_types.empty:
            fig_pie = px.pie(crime_types, values='count', names='crime_type',
                           title="Distribution of Crime Types")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No crime type data available")
    
    # Severity distribution
    st.subheader("⚠️ Severity Analysis")
    
    severity_data = pd.read_sql_query("""
        SELECT severity_level, COUNT(*) as count 
        FROM Complaints 
        GROUP BY severity_level
    """, conn)
    
    if not severity_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_severity = px.bar(severity_data, x='severity_level', y='count',
                                color='severity_level',
                                color_discrete_map={
                                    'Low': '#44aa44',
                                    'Medium': '#ff8800', 
                                    'High': '#ff4444'
                                },
                                title="Complaints by Severity Level")
            st.plotly_chart(fig_severity, use_container_width=True)
        
        with col2:
            # Display severity statistics
            for _, row in severity_data.iterrows():
                severity = str(row['severity_level'])
                count = int(row['count'])
                percentage = (count / total_complaints * 100) if total_complaints > 0 else 0
                color = get_severity_color(severity.lower())
                
                st.markdown(f"""
                <div style="padding: 10px; margin: 5px 0; border-left: 5px solid {color}; background-color: #f8f9fa;">
                    <strong>{severity} Severity:</strong> {count} cases ({percentage:.1f}%)
                </div>
                """, unsafe_allow_html=True)
    
    # Crime mapping
    st.subheader("🗺️ Crime Location Map")
    
    # Get complaints with location data
    location_data = pd.read_sql_query("""
        SELECT crime_type, severity_level, latitude, longitude, location, date_filed
        FROM Complaints 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY date_filed DESC
        LIMIT 100
    """, conn)
    
    if not location_data.empty:
        # Create folium map centered on Kerala
        kerala_center = [10.8505, 76.2711]
        crime_map = folium.Map(location=kerala_center, zoom_start=7)
        
        # Color mapping for severity
        severity_colors = {
            'Low': 'green',
            'Medium': 'orange', 
            'High': 'red'
        }
        
        # Add markers for each crime
        for idx, row in location_data.iterrows():
            color = severity_colors.get(str(row['severity_level']), 'blue')
            
            folium.CircleMarker(
                location=[float(row['latitude']), float(row['longitude'])],
                radius=8,
                popup=f"""
                <b>Crime:</b> {row['crime_type']}<br>
                <b>Severity:</b> {row['severity_level']}<br>
                <b>Location:</b> {row['location']}<br>
                <b>Date:</b> {row['date_filed']}
                """,
                color='black',
                weight=1,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(crime_map)
        
        # Display map
        map_data = st_folium(crime_map, width=700, height=500)
    else:
        st.info("No location data available for mapping")
    
    # Recent complaints table
    st.subheader("📋 Recent Complaints")
    
    recent_complaints = pd.read_sql_query("""
        SELECT reference_number, crime_type, severity_level, location, status, date_filed
        FROM Complaints 
        ORDER BY date_filed DESC 
        LIMIT 10
    """, conn)
    
    if not recent_complaints.empty:
        # Format the data for display
        display_df = recent_complaints.copy()
        display_df['date_filed'] = pd.to_datetime(display_df['date_filed']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(
            display_df,
            column_config={
                "reference_number": "Reference #",
                "crime_type": "Crime Type",
                "severity_level": st.column_config.TextColumn(
                    "Severity",
                    help="Crime severity level"
                ),
                "location": "Location",
                "status": "Status",
                "date_filed": "Date Filed"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No recent complaints to display")
    
    conn.close()

def login_page():
    """Display login and registration page"""
    st.title("🔐 Login / Register")
    
    tab1, tab2 = st.tabs(["👤 Login", "📝 Register"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("👤 Citizen Login")
            login_form()
        
        with col2:
            st.subheader("👮 Officer Login") 
            with st.form("officer_login"):
                badge_number = st.text_input("Badge Number", placeholder="Enter badge number")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                
                submitted = st.form_submit_button("Login", use_container_width=True)
                
                if submitted:
                    if badge_number and password:
                        user = db.get_user_by_badge(badge_number)
                        if user and user['password_hash'] == hash_password(password):
                            st.session_state.user = user
                            st.success(f"Welcome, Officer {user['name']} 🎉")
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials")
                    else:
                        st.error("⚠️ Please fill in all fields")
    
    with tab2:
        register_form()

def submit_complaint():
    """Citizen complaint submission form"""
    require_auth('citizen')
    
    st.title("📝 Submit New Complaint")
    
    with st.form("complaint_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            current_user = get_current_user()
            citizen_name = st.text_input("Full Name*", value=current_user['name'] if current_user else '')
            citizen_email = st.text_input("Email*", value=current_user['email'] if current_user else '')
            citizen_phone = st.text_input("Phone Number*", value=current_user.get('phone', '') if current_user else '')
        
        with col2:
            crime_type = st.selectbox("Crime Type*", [
                "Theft", "Fraud", "Assault", "Harassment", "Cybercrime", 
                "Property Damage", "Domestic Violence", "Traffic Violation",
                "Corruption", "Missing Person", "Other"
            ])
            
            incident_date = st.date_input("Incident Date*", max_value=datetime.now().date())
            
            location = st.text_input("Location/Address*", placeholder="Enter incident location")
        
        # Location coordinates (optional)
        st.subheader("📍 Location Coordinates (Optional)")
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.number_input("Latitude", value=None, format="%.6f")
        with col2:
            longitude = st.number_input("Longitude", value=None, format="%.6f")
        
        # Complaint details
        st.subheader("📋 Complaint Details")
        description = st.text_area("Incident Description*", 
                                 placeholder="Please provide detailed description of the incident...",
                                 height=150)
        
        # Evidence upload
        st.subheader("📎 Supporting Evidence (Optional)")
        uploaded_files = st.file_uploader(
            "Upload evidence files (photos, documents, audio, video)",
            type=None,
            accept_multiple_files=True,
            help="You can upload multiple files. Allowed: Images, PDFs, Documents, Audio, Video (Max 10MB each)"
        )
        
        evidence_descriptions = {}
        if uploaded_files:
            st.write("**File Descriptions:**")
            for i, file in enumerate(uploaded_files):
                evidence_descriptions[file.name] = st.text_input(
                    f"Description for {file.name} (optional)",
                    key=f"desc_{i}",
                    placeholder="What does this evidence show?"
                )
        
        # Severity will be auto-classified
        submitted = st.form_submit_button("🚨 Submit Complaint", use_container_width=True)
        
        if submitted:
            if all([citizen_name, citizen_email, citizen_phone, crime_type, incident_date, location, description]):
                # Classify severity automatically
                severity_level = classify_severity(crime_type, description, crime_type)
                severity_score = {'low': 1, 'medium': 5, 'high': 10}[severity_level]
                
                # Prepare complaint data
                complaint_data = {
                    'citizen_name': citizen_name,
                    'citizen_email': citizen_email, 
                    'citizen_phone': citizen_phone,
                    'crime_type': crime_type,
                    'description': description,
                    'location': location,
                    'latitude': latitude,
                    'longitude': longitude,
                    'incident_date': incident_date,
                    'severity_level': severity_level.title(),
                    'severity_score': severity_score
                }
                
                try:
                    reference_number = db.submit_complaint(complaint_data)
                    
                    # Get the complaint ID for evidence upload
                    complaint_record = db.get_complaint_by_reference(reference_number)
                    complaint_id = complaint_record['complaint_id'] if complaint_record else None
                    
                    # Process evidence files if any
                    evidence_uploaded = 0
                    if uploaded_files and complaint_id:
                        from evidence_handler import save_uploaded_file, get_file_type
                        
                        for file in uploaded_files:
                            success, file_path, error_msg = save_uploaded_file(file, complaint_id)
                            
                            if success:
                                # Add to database
                                file_type = get_file_type(file.name)
                                file_description = evidence_descriptions.get(file.name, "")
                                
                                evidence_id = db.add_evidence(
                                    complaint_id=complaint_id,
                                    file_name=file.name,
                                    file_path=file_path,
                                    file_type=file_type,
                                    file_size=file.size,
                                    uploaded_by=citizen_email,
                                    description=file_description
                                )
                                
                                if evidence_id:
                                    evidence_uploaded += 1
                                else:
                                    st.warning(f"⚠️ Failed to save evidence record for {file.name}")
                            else:
                                st.warning(f"⚠️ Failed to upload {file.name}: {error_msg}")
                    
                    st.success(f"✅ Complaint submitted successfully!")
                    st.info(f"📋 Your reference number: **{reference_number}**")
                    if evidence_uploaded > 0:
                        st.success(f"📎 {evidence_uploaded} evidence file(s) uploaded successfully!")
                    st.info("Please save this reference number for tracking your complaint.")
                    
                except Exception as e:
                    st.error(f"❌ Error submitting complaint: {str(e)}")
            else:
                st.error("⚠️ Please fill in all required fields marked with *")

def my_complaints():
    """Display citizen's complaints with advanced search"""
    require_auth('citizen')
    
    st.title("📋 My Complaints")
    
    current_user = get_current_user()
    
    # Check if user has any complaints first
    conn = db.connect()
    complaint_count = pd.read_sql_query("""
        SELECT COUNT(*) as count FROM Complaints 
        WHERE citizen_email = ?
    """, conn, params=[current_user['email']]).iloc[0]['count']
    conn.close()
    
    if complaint_count == 0:
        st.info("You have not submitted any complaints yet.")
        if st.button("📝 Submit Your First Complaint"):
            st.session_state.page = 'submit_complaint'
            st.rerun()
    else:
        st.write(f"Total Complaints: {complaint_count}")
        
        # Import and display advanced search
        from complaint_search import display_advanced_complaint_search
        display_advanced_complaint_search(user_role='citizen', user_id=current_user['user_id'])

def officer_dashboard():
    """Police officer dashboard"""
    require_auth('police')
    
    st.title("👮 Officer Dashboard")
    
    current_user = get_current_user()
    st.write(f"Welcome, Officer {current_user['name']} (Badge: {current_user.get('badge_number', 'N/A')})")
    
    # Officer statistics
    conn = db.connect()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        assigned_cases = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM Complaints 
            WHERE assigned_officer_id = ?
        """, conn, params=[current_user['user_id']]).iloc[0]['count']
        st.metric("Assigned Cases", assigned_cases)
    
    with col2:
        resolved_cases = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM Complaints 
            WHERE assigned_officer_id = ? AND status = 'Resolved'
        """, conn, params=[current_user['user_id']]).iloc[0]['count']
        st.metric("Resolved Cases", resolved_cases)
    
    with col3:
        pending_cases = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM Complaints 
            WHERE assigned_officer_id = ? AND status IN ('Pending', 'Under Investigation')
        """, conn, params=[current_user['user_id']]).iloc[0]['count']
        st.metric("Active Cases", pending_cases)
    
    with col4:
        fir_count = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM Cases 
            WHERE police_officer_id = ?
        """, conn, params=[current_user['user_id']]).iloc[0]['count']
        st.metric("FIRs Filed", fir_count)
    
    st.write("---")
    
    # Recent assigned complaints
    st.subheader("📂 Recent Assigned Cases")
    
    recent_assigned = pd.read_sql_query("""
        SELECT reference_number, crime_type, severity_level, status, date_filed, location
        FROM Complaints 
        WHERE assigned_officer_id = ? 
        ORDER BY date_filed DESC 
        LIMIT 5
    """, conn, params=[current_user['user_id']])
    
    if not recent_assigned.empty:
        st.dataframe(recent_assigned, use_container_width=True, hide_index=True)
    else:
        st.info("No cases assigned yet.")
    
    conn.close()

def search_all_complaints():
    """Advanced search for all complaints - officers only"""
    require_auth('police')
    
    st.title("🔍 Search All Complaints")
    
    current_user = get_current_user()
    
    # Import and display advanced search
    from complaint_search import display_advanced_complaint_search
    display_advanced_complaint_search(user_role='police', user_id=current_user['user_id'])

def pending_complaints():
    """Display and manage pending complaints"""
    require_auth('police')
    
    st.title("📂 Pending Complaints")
    
    current_user = get_current_user()
    
    # Get pending complaints
    pending_complaints_data = db.get_pending_complaints()
    
    if not pending_complaints_data:
        st.info("No pending complaints at this time.")
        return
    
    st.write(f"Total Pending Complaints: {len(pending_complaints_data)}")
    
    # Severity filter
    severity_filter = st.selectbox("Filter by Severity", 
                                 ['All', 'High', 'Medium', 'Low'])
    
    if severity_filter != 'All':
        filtered_complaints = [c for c in pending_complaints_data if c['severity_level'] == severity_filter]
    else:
        filtered_complaints = pending_complaints_data
    
    # Display complaints
    for complaint in filtered_complaints:
        with st.expander(f"🚨 {complaint['reference_number']} - {complaint['crime_type']} - {(complaint['severity_level'].upper())}", 
                       expanded=False):
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Reference:** {complaint['reference_number']}")
                st.write(f"**Crime Type:** {complaint['crime_type']}")
                st.write(f"**Citizen:** {complaint['citizen_name']}")
                st.write(f"**Phone:** {complaint['citizen_phone']}")
                st.write(f"**Location:** {complaint['location']}")
            
            with col2:
                st.write(f"**Date Filed:** {complaint['date_filed']}")
                st.write(f"**Incident Date:** {complaint['incident_date']}")
                severity_badge = get_severity_badge(complaint['severity_level'].lower())
                st.markdown(f"**Severity:** {severity_badge}", unsafe_allow_html=True)
                st.write(f"**Status:** {complaint['status']}")
            
            st.write("**Description:**")
            st.write(complaint['description'])
            
            # Display evidence files if any
            evidence_list = db.get_evidence_by_complaint(complaint['complaint_id'])
            if evidence_list:
                from evidence_handler import display_evidence_list
                display_evidence_list(evidence_list, show_actions=True)
            
            # Legal suggestions
            from legal_database import get_law_suggestions, display_law_suggestions
            suggestions = get_law_suggestions(complaint['description'], complaint['crime_type'])
            if suggestions:
                st.write("**💡 Suggested Legal References:**")
                for suggestion in suggestions:
                    st.write(f"• {suggestion}")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"🔍 Investigate", key=f"investigate_{complaint['complaint_id']}"):
                    try:
                        db.update_complaint_status(
                            complaint['complaint_id'], 
                            'Under Investigation', 
                            current_user.get('badge_number', 'N/A'),
                            f"Investigation started by Officer {current_user['name']}"
                        )
                        st.success("Status updated to 'Under Investigation'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating status: {str(e)}")
            
            with col2:
                if st.button(f"✅ Resolve", key=f"resolve_{complaint['complaint_id']}"):
                    try:
                        db.update_complaint_status(
                            complaint['complaint_id'],
                            'Resolved',
                            current_user.get('badge_number', 'N/A'),
                            f"Case resolved by Officer {current_user['name']}"
                        )
                        st.success("Case marked as resolved")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error resolving case: {str(e)}")
            
            with col3:
                if st.button(f"📄 File FIR", key=f"fir_{complaint['complaint_id']}"):
                    st.session_state[f'file_fir_{complaint["complaint_id"]}'] = True
            
            # FIR Filing Form
            if st.session_state.get(f'file_fir_{complaint["complaint_id"]}', False):
                with st.form(f"fir_form_{complaint['complaint_id']}"):
                    st.write("**File FIR for this complaint:**")
                    
                    fir_notes = st.text_area("Case Notes", placeholder="Enter case notes and FIR details...")
                    
                    col_file, col_cancel = st.columns(2)
                    
                    with col_file:
                        if st.form_submit_button("📄 File FIR", type="primary"):
                            try:
                                # Register case and generate PDF
                                db.register_case(
                                    complaint['complaint_id'],
                                    current_user['user_id'],
                                    f"case_pdfs/case_{complaint['complaint_id']}.pdf"
                                )
                                
                                # Update status to Under Investigation
                                db.update_complaint_status(
                                    complaint['complaint_id'],
                                    'Under Investigation',
                                    current_user.get('badge_number', 'N/A'),
                                    f"FIR filed by Officer {current_user['name']}. {fir_notes}"
                                )
                                
                                st.success("FIR filed successfully!")
                                st.session_state[f'file_fir_{complaint["complaint_id"]}'] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error filing FIR: {str(e)}")
                    
                    with col_cancel:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f'file_fir_{complaint["complaint_id"]}'] = False
                            st.rerun()

def case_management():
    """Case management for officers"""
    require_auth('police')
    
    st.title("📄 Case Management")
    
    current_user = get_current_user()
    
    # Get officer's cases
    conn = db.connect()
    officer_cases = pd.read_sql_query("""
        SELECT c.case_id, c.complaint_id, c.case_status, c.date_registered,
               comp.reference_number, comp.crime_type, comp.citizen_name, comp.severity_level
        FROM Cases c
        JOIN Complaints comp ON c.complaint_id = comp.complaint_id
        WHERE c.police_officer_id = ?
        ORDER BY c.date_registered DESC
    """, conn, params=[current_user['user_id']])
    
    if officer_cases.empty:
        st.info("No cases registered yet.")
        return
    
    st.write(f"Total Cases: {len(officer_cases)}")
    
    # Status filter
    status_filter = st.selectbox("Filter by Status", 
                               ['All'] + list(officer_cases['case_status'].unique()))
    
    if status_filter != 'All':
        filtered_cases = officer_cases[officer_cases['case_status'] == status_filter]
    else:
        filtered_cases = officer_cases
    
    # Display cases
    for _, case in filtered_cases.iterrows():
        with st.expander(f"📁 Case {case['reference_number']} - {case['crime_type']}", 
                       expanded=False):
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Reference:** {case['reference_number']}")
                st.write(f"**Crime Type:** {case['crime_type']}")
                st.write(f"**Citizen:** {case['citizen_name']}")
                st.write(f"**Registered:** {case['date_registered']}")
            
            with col2:
                st.write(f"**Status:** {case['case_status']}")
                severity_badge = get_severity_badge(case['severity_level'].lower())
                st.markdown(f"**Severity:** {severity_badge}", unsafe_allow_html=True)
            
            # Display evidence files if any
            evidence_list = db.get_evidence_by_complaint(case['complaint_id'])
            if evidence_list:
                from evidence_handler import display_evidence_list
                display_evidence_list(evidence_list, show_actions=True)
            
            # Case actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"📄 Generate PDF", key=f"pdf_{case['case_id']}"):
                    try:
                        pdf_path = generate_case_pdf(case['case_id'])
                        if pdf_path:
                            st.success("PDF generated successfully!")
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=pdf_file.read(),
                                    file_name=f"case_{case['reference_number']}.pdf",
                                    mime="application/pdf"
                                )
                        else:
                            st.error("Failed to generate PDF")
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
            
            with col2:
                if st.button(f"🔄 Update Status", key=f"update_{case['case_id']}"):
                    st.session_state[f'update_case_{case["case_id"]}'] = True
            
            with col3:
                if st.button(f"📋 View Details", key=f"details_{case['case_id']}"):
                    # Get complaint details
                    complaint = db.get_complaint_by_reference(case['reference_number'])
                    if complaint:
                        st.write("**Complaint Details:**")
                        st.write(complaint['description'])
            
            # Update case status form
            if st.session_state.get(f'update_case_{case["case_id"]}', False):
                with st.form(f"update_form_{case['case_id']}"):
                    new_status = st.selectbox("New Status", 
                                            ['Pending', 'Under Investigation', 'Resolved', 'Closed'])
                    update_notes = st.text_area("Update Notes")
                    
                    col_update, col_cancel = st.columns(2)
                    
                    with col_update:
                        if st.form_submit_button("Update Status", type="primary"):
                            try:
                                db.update_complaint_status(
                                    case['complaint_id'],
                                    new_status,
                                    current_user.get('badge_number', 'N/A'),
                                    update_notes
                                )
                                st.success("Status updated successfully!")
                                st.session_state[f'update_case_{case["case_id"]}'] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating status: {str(e)}")
                    
                    with col_cancel:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f'update_case_{case["case_id"]}'] = False
                            st.rerun()
    
    conn.close()

def analytics_dashboard_page():
    """Analytics dashboard page for police officers"""
    require_auth('police')
    
    from analytics_dashboard import display_analytics_dashboard
    display_analytics_dashboard()

def main():
    """Main application function"""
    init_session_state()
    
    # Sidebar navigation
    selected_page = sidebar_navigation()
    
    # Handle logout
    if selected_page == "logout":
        logout()
        return
    
    # Route to appropriate page
    if selected_page == "dashboard":
        crime_dashboard()
    elif selected_page == "login":
        login_page()
    elif selected_page == "submit_complaint":
        submit_complaint()
    elif selected_page == "my_complaints":
        my_complaints()
    elif selected_page == "officer_dashboard":
        officer_dashboard()
    elif selected_page == "pending_complaints":
        pending_complaints()
    elif selected_page == "search_complaints":
        search_all_complaints()
    elif selected_page == "case_management":
        case_management()
    elif selected_page == "analytics":
        analytics_dashboard_page()
    elif selected_page == "legal_database":
        display_legal_database()

if __name__ == "__main__":
    main()
