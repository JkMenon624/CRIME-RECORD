import streamlit as st
from database import db

def display_legal_database():
    """Display the legal database interface with search and filtering"""
    
    st.subheader("🔍 Search Legal References")
    
    # Search and filter controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input(
            "Search laws by keywords, section, or description",
            placeholder="e.g., theft, murder, section 103, intimidation"
        )
    
    with col2:
        law_type_filter = st.selectbox("Filter by Type", ["All", "BNS", "BNSS"])
    
    with col3:
        results_per_page = st.selectbox("Results per page", [10, 20, 50], index=1)
    
    # Search button
    if st.button("🔍 Search Laws", use_container_width=True) or search_query:
        # Perform search
        law_type = law_type_filter if law_type_filter != "All" else ""
        laws = db.search_laws(search_query, law_type)
        
        if not laws:
            st.info("No laws found matching your search criteria.")
        else:
            st.success(f"Found {len(laws)} law(s) matching your search.")
            
            # Pagination
            total_laws = len(laws)
            total_pages = (total_laws - 1) // results_per_page + 1
            
            if 'legal_page' not in st.session_state:
                st.session_state.legal_page = 1
            
            # Page navigation
            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    if st.button("← Previous", disabled=st.session_state.legal_page <= 1):
                        st.session_state.legal_page -= 1
                        st.rerun()
                
                with col2:
                    st.write(f"Page {st.session_state.legal_page} of {total_pages}")
                
                with col3:
                    if st.button("Next →", disabled=st.session_state.legal_page >= total_pages):
                        st.session_state.legal_page += 1
                        st.rerun()
            
            # Calculate pagination bounds
            start_idx = (st.session_state.legal_page - 1) * results_per_page
            end_idx = min(start_idx + results_per_page, total_laws)
            
            # Display laws
            for law in laws[start_idx:end_idx]:
                display_law_card(law)
    
    else:
        # Display recent/popular laws by default
        st.subheader("📚 Browse Legal References")
        
        # Quick access tabs
        tab1, tab2 = st.tabs(["🏛️ BNS (Bharatiya Nyaya Sanhita)", "⚖️ BNSS (Bharatiya Nagarik Suraksha Sanhita)"])
        
        with tab1:
            st.write("**Bharatiya Nyaya Sanhita** - Criminal Law")
            bns_laws = db.search_laws("", "BNS")
            
            if bns_laws:
                st.write(f"Total BNS Sections: {len(bns_laws)}")
                
                # Display first few BNS laws
                for law in bns_laws[:5]:
                    display_law_card(law, compact=True)
                
                if len(bns_laws) > 5:
                    if st.button("View All BNS Sections"):
                        st.session_state.show_all_bns = True
                        st.rerun()
        
        with tab2:
            st.write("**Bharatiya Nagarik Suraksha Sanhita** - Criminal Procedure")
            bnss_laws = db.search_laws("", "BNSS")
            
            if bnss_laws:
                st.write(f"Total BNSS Sections: {len(bnss_laws)}")
                
                # Display first few BNSS laws
                for law in bnss_laws[:5]:
                    display_law_card(law, compact=True)
                
                if len(bnss_laws) > 5:
                    if st.button("View All BNSS Sections"):
                        st.session_state.show_all_bnss = True
                        st.rerun()

def display_law_card(law, compact=False):
    """Display a law in a card format"""
    law_id, law_type, section_number, title, description, punishment, keywords, created_at = law
    
    # Color coding for law types
    type_colors = {
        'BNS': '#dc3545',    # Red for criminal law
        'BNSS': '#007bff'    # Blue for procedure
    }
    
    type_color = type_colors.get(law_type, '#6c757d')
    
    # Create expandable card
    with st.expander(f"{law_type} Section {section_number}: {title}", expanded=False):
        # Law type badge
        st.markdown(f"""
        <span style="
            background-color: {type_color};
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 10px;
            display: inline-block;
        ">
            {law_type} § {section_number}
        </span>
        """, unsafe_allow_html=True)
        
        # Description
        st.write("**Description:**")
        st.write(description)
        
        # Punishment (if available)
        if punishment:
            st.write("**Punishment:**")
            st.write(punishment)
        
        # Keywords
        if keywords:
            st.write("**Keywords:**")
            keyword_list = [kw.strip() for kw in keywords.split(',')]
            keyword_badges = []
            for keyword in keyword_list:
                keyword_badges.append(f"""
                <span style="
                    background-color: #e9ecef;
                    color: #495057;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    margin-right: 5px;
                    display: inline-block;
                    margin-bottom: 5px;
                ">
                    {keyword}
                </span>
                """)
            
            st.markdown(''.join(keyword_badges), unsafe_allow_html=True)
        
        # Action buttons for police officers
        if st.session_state.get('user', {}).get('role') == 'police':
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"📋 Copy Section Reference", key=f"copy_{law_id}"):
                    reference_text = f"{law_type} Section {section_number}: {title}"
                    st.success(f"Reference copied: {reference_text}")
            
            with col2:
                if st.button(f"📎 Add to Case", key=f"add_case_{law_id}"):
                    st.session_state[f'add_to_case_{law_id}'] = True
            
            # Add to case form
            if st.session_state.get(f'add_to_case_{law_id}', False):
                with st.form(f"add_law_form_{law_id}"):
                    st.write("**Add this law to a case:**")
                    
                    # Get active cases for this officer
                    current_user = st.session_state.get('user', {})
                    if current_user:
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            SELECT case_id, case_number, comp.title
                            FROM cases c
                            JOIN complaints comp ON c.complaint_id = comp.complaint_id
                            WHERE c.officer_id = ? AND c.status = 'active'
                            ORDER BY c.registration_date DESC
                        ''', (current_user['user_id'],))
                        
                        active_cases = cursor.fetchall()
                        conn.close()
                        
                        if active_cases:
                            case_options = {f"{case[1]} - {case[2]}": case[0] for case in active_cases}
                            selected_case = st.selectbox("Select Case", list(case_options.keys()))
                            
                            col_add, col_cancel = st.columns(2)
                            
                            with col_add:
                                if st.form_submit_button("Add Law to Case", type="primary"):
                                    case_id = case_options[selected_case]
                                    
                                    # Add law to case
                                    conn = db.get_connection()
                                    cursor = conn.cursor()
                                    
                                    try:
                                        cursor.execute('''
                                            INSERT OR IGNORE INTO case_laws (case_id, law_id)
                                            VALUES (?, ?)
                                        ''', (case_id, law_id))
                                        conn.commit()
                                        st.success(f"Law added to case {selected_case}")
                                    except Exception as e:
                                        st.error(f"Error adding law to case: {str(e)}")
                                    finally:
                                        conn.close()
                                    
                                    st.session_state[f'add_to_case_{law_id}'] = False
                                    st.rerun()
                            
                            with col_cancel:
                                if st.form_submit_button("Cancel"):
                                    st.session_state[f'add_to_case_{law_id}'] = False
                                    st.rerun()
                        else:
                            st.info("No active cases found. Register a case first to add laws.")

def get_law_suggestions(complaint_text, category):
    """Get suggested laws based on complaint content"""
    # Simple keyword-based law suggestion
    suggestions = []
    
    text_lower = complaint_text.lower()
    category_lower = category.lower()
    
    # Define law suggestions based on keywords and categories
    law_mappings = {
        'murder': ['BNS', '103'],
        'kill': ['BNS', '103'],
        'death': ['BNS', '103'],
        'theft': ['BNS', '304'],
        'steal': ['BNS', '304'],
        'robbery': ['BNS', '304'],
        'assault': ['BNS', '354'],
        'harassment': ['BNS', '354'],
        'fraud': ['BNS', '420'],
        'cheat': ['BNS', '420'],
        'scam': ['BNS', '420'],
        'threat': ['BNS', '506'],
        'intimidation': ['BNS', '506'],
        'blackmail': ['BNS', '506']
    }
    
    # Search for matching laws
    conn = db.get_connection()
    cursor = conn.cursor()
    
    for keyword, (law_type, section) in law_mappings.items():
        if keyword in text_lower or keyword in category_lower:
            cursor.execute('''
                SELECT * FROM laws 
                WHERE law_type = ? AND section_number = ?
            ''', (law_type, section))
            
            law = cursor.fetchone()
            if law and law not in suggestions:
                suggestions.append(law)
    
    conn.close()
    return suggestions

def display_law_suggestions(complaint_text, category):
    """Display suggested laws for a complaint"""
    suggestions = get_law_suggestions(complaint_text, category)
    
    if suggestions:
        st.subheader("💡 Suggested Legal References")
        st.info("Based on the complaint content, these laws might be applicable:")
        
        for law in suggestions:
            display_law_card(law, compact=True)
    
    return suggestions
