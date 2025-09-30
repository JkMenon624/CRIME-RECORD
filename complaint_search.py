import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import Database

def display_advanced_complaint_search(user_role='citizen', user_id=None):
    """
    Display advanced complaint search interface with comprehensive filtering options
    
    Args:
        user_role: 'citizen', 'police', or 'admin'
        user_id: ID of current user (for citizen-specific filtering)
    """
    
    db = Database()
    
    st.subheader("🔍 Advanced Complaint Search")
    
    # Initialize session state for filters
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Get statistics for dynamic filters
    stats = db.get_complaint_statistics()
    
    # Search filters in collapsible sections
    with st.expander("🔧 Search Filters", expanded=True):
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📝 Text Search**")
            search_query = st.text_input(
                "Search in reference, crime type, location, description, citizen name",
                placeholder="Enter keywords, reference number, or location...",
                help="Search across multiple fields including reference number, crime type, location, and description"
            )
            
            st.write("**📅 Date Range**")
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input(
                    "From Date",
                    value=date.today() - timedelta(days=30),
                    max_value=date.today(),
                    help="Filter complaints from this date onwards"
                )
            with date_col2:
                end_date = st.date_input(
                    "To Date",
                    value=date.today(),
                    max_value=date.today(),
                    help="Filter complaints up to this date"
                )
        
        with col2:
            st.write("**🏷️ Category Filters**")
            
            # Severity filter
            severity_options = ['All', 'High', 'Medium', 'Low']
            severity_filter = st.selectbox(
                "Severity Level",
                severity_options,
                help="Filter by complaint severity level"
            )
            
            # Status filter
            status_options = ['All', 'Pending', 'Under Investigation', 'Resolved', 'Closed']
            if user_role == 'citizen':
                status_filter = st.selectbox(
                    "Status",
                    status_options,
                    help="Filter by complaint status"
                )
            else:
                status_filter = st.selectbox(
                    "Status",
                    status_options,
                    help="Filter by complaint status"
                )
            
            # Crime type filter
            crime_type_options = ['All'] + stats['crime_types']
            crime_type_filter = st.selectbox(
                "Crime Type",
                crime_type_options,
                help="Filter by specific crime type"
            )
            
            # Location filter
            location_filter = st.text_input(
                "Location Filter",
                placeholder="Enter city, district, or area...",
                help="Filter by location (partial match supported)"
            )
        
        # Results per page
        results_per_page = st.selectbox(
            "Results per page",
            [10, 20, 50, 100],
            index=1,
            help="Number of results to display per page"
        )
    
    # Search button
    search_button = st.button("🔍 Search Complaints", use_container_width=True, type="primary")
    
    # Perform search when button clicked or on page load
    if search_button or st.session_state.get('auto_search', False):
        
        # Reset page number on new search
        if search_button:
            st.session_state.current_page = 1
        
        # Calculate pagination
        offset = (st.session_state.current_page - 1) * results_per_page
        
        # Build filters
        filters = {
            'search_query': search_query,
            'severity_filter': severity_filter,
            'location_filter': location_filter,
            'start_date': start_date,
            'end_date': end_date,
            'status_filter': status_filter,
            'crime_type_filter': crime_type_filter,
            'limit': results_per_page,
            'offset': offset
        }
        
        # For citizens, only show their own complaints
        if user_role == 'citizen' and user_id:
            # Get user email for filtering
            user_data = db.get_user_by_id(user_id)
            if user_data:
                citizen_email = user_data.get('email')
                filters['citizen_email'] = citizen_email
                results = db.search_complaints_advanced(**filters)
                # Get total count for pagination
                count_filters = {k: v for k, v in filters.items() if k not in ['limit', 'offset']}
                total_results = db.count_complaints_advanced(**count_filters)
            else:
                results = []
                total_results = 0
        else:
            results = db.search_complaints_advanced(**filters)
            # Get total count for pagination
            count_filters = {k: v for k, v in filters.items() if k not in ['limit', 'offset']}
            total_results = db.count_complaints_advanced(**count_filters)
        
        st.session_state.search_results = results
        
        # Display results summary
        if results:
            st.success(f"Found {total_results} complaint(s) matching your criteria (showing {len(results)} on this page)")
            
            # Pagination controls
            total_pages = (total_results - 1) // results_per_page + 1 if total_results > 0 else 1
            
            if total_pages > 1:
                st.write("---")
                col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
                
                with col1:
                    if st.button("⏮️ First", disabled=st.session_state.current_page <= 1):
                        st.session_state.current_page = 1
                        st.session_state.auto_search = True
                        st.rerun()
                
                with col2:
                    if st.button("◀️ Previous", disabled=st.session_state.current_page <= 1):
                        st.session_state.current_page -= 1
                        st.session_state.auto_search = True
                        st.rerun()
                
                with col3:
                    st.write(f"**Page {st.session_state.current_page} of {total_pages}** ({total_results} total results)")
                
                with col4:
                    if st.button("Next ▶️", disabled=st.session_state.current_page >= total_pages):
                        st.session_state.current_page += 1
                        st.session_state.auto_search = True
                        st.rerun()
                
                with col5:
                    if st.button("Last ⏭️", disabled=st.session_state.current_page >= total_pages):
                        st.session_state.current_page = total_pages
                        st.session_state.auto_search = True
                        st.rerun()
            
            # Display results
            display_search_results(results, user_role)
            
        else:
            st.info("No complaints found matching your search criteria. Try adjusting the filters.")
    
    # Reset auto_search flag
    if 'auto_search' in st.session_state:
        st.session_state.auto_search = False

def display_search_results(results, user_role):
    """Display search results in a formatted layout"""
    
    for complaint in results:
        
        # Create severity badge
        severity = complaint.get('severity_level', 'Unknown').lower()
        if severity == 'high':
            severity_badge = "🔴 **HIGH**"
        elif severity == 'medium':
            severity_badge = "🟡 **MEDIUM**"
        elif severity == 'low':
            severity_badge = "🟢 **LOW**"
        else:
            severity_badge = "⚪ **UNKNOWN**"
        
        # Status badge
        status = complaint.get('status', 'Unknown')
        if status == 'Pending':
            status_badge = "⏳ Pending"
        elif status == 'Under Investigation':
            status_badge = "🔍 Under Investigation"
        elif status == 'Resolved':
            status_badge = "✅ Resolved"
        elif status == 'Closed':
            status_badge = "❌ Closed"
        else:
            status_badge = f"📋 {status}"
        
        # Display complaint card
        with st.expander(
            f"📋 {complaint['reference_number']} - {complaint['crime_type']} - {severity_badge}",
            expanded=False
        ):
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**📄 Reference:** {complaint['reference_number']}")
                st.write(f"**🚨 Crime Type:** {complaint['crime_type']}")
                st.write(f"**📍 Location:** {complaint['location']}")
                st.write(f"**📅 Date Filed:** {complaint['date_filed']}")
                if complaint.get('incident_date'):
                    st.write(f"**⏰ Incident Date:** {complaint['incident_date']}")
            
            with col2:
                st.write(f"**📊 Status:** {status_badge}")
                st.markdown(f"**⚠️ Severity:** {severity_badge}")
                if user_role in ['police', 'admin']:
                    st.write(f"**👤 Citizen:** {complaint.get('citizen_name', 'N/A')}")
                    st.write(f"**📞 Phone:** {complaint.get('citizen_phone', 'N/A')}")
                if complaint.get('assigned_officer'):
                    st.write(f"**👮 Assigned Officer:** {complaint['assigned_officer']}")
            
            st.write("**📝 Description:**")
            st.write(complaint.get('description', 'No description available'))
            
            # Display evidence files if any
            from database import Database
            from evidence_handler import display_evidence_list
            db = Database()
            evidence_list = db.get_evidence_by_complaint(complaint['complaint_id'])
            if evidence_list:
                display_evidence_list(evidence_list, show_actions=False)
            
            # Additional actions based on user role
            if user_role == 'police':
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"🔍 Investigate", key=f"investigate_{complaint['complaint_id']}"):
                        st.session_state.selected_complaint = complaint['complaint_id']
                        st.session_state.page = 'pending_complaints'
                        st.rerun()
                
                with col2:
                    if st.button(f"📄 View Details", key=f"details_{complaint['complaint_id']}"):
                        st.session_state.selected_complaint = complaint['complaint_id']
                        st.session_state.page = 'case_management'
                        st.rerun()
                
                with col3:
                    if complaint['status'] == 'Pending':
                        if st.button(f"📝 File FIR", key=f"fir_{complaint['complaint_id']}"):
                            st.session_state.selected_complaint = complaint['complaint_id']
                            st.session_state.page = 'pending_complaints'
                            st.rerun()

def get_severity_badge(severity):
    """Get HTML badge for severity level"""
    if severity == 'high':
        return '<span style="background-color: #ff4444; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">🔴 HIGH</span>'
    elif severity == 'medium':
        return '<span style="background-color: #ff8800; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">🟡 MEDIUM</span>'
    elif severity == 'low':
        return '<span style="background-color: #44aa44; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">🟢 LOW</span>'
    else:
        return '<span style="background-color: #888888; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">⚪ UNKNOWN</span>'