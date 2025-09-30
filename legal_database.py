import streamlit as st
from database import Database

# Initialize database
db = Database()

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
        # Reset pagination when performing new search
        if 'last_search_query' not in st.session_state or st.session_state.last_search_query != search_query:
            st.session_state.legal_page = 1
            st.session_state.last_search_query = search_query
        
        # Perform search
        law_type = law_type_filter if law_type_filter != "All" else ""
        laws = db.search_laws(search_query, law_type)
        
        if not laws:
            st.info("No laws found matching your search criteria. Legal database is being updated with latest Indian legal documents.")
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
        # Display information about legal database
        st.subheader("📚 Legal Database Information")
        
        st.info("""
        **Legal Database Status:** Currently being populated with the latest Indian legal documents.
        
        **Available References:**
        - 🏛️ **BNS (Bharatiya Nyaya Sanhita)** - New Criminal Law replacing IPC
        - ⚖️ **BNSS (Bharatiya Nagarik Suraksha Sanhita)** - New Criminal Procedure replacing CrPC
        - 📜 **Constitution of India** - Fundamental rights and legal framework
        
        **Features:**
        - Advanced search functionality
        - Section-wise organization
        - Keywords and punishment details
        - Case law integration for officers
        """)
        
        # Quick access to common sections
        st.subheader("🔗 Quick Access")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Common BNS Sections:**")
            st.write("- Section 103: Murder")
            st.write("- Section 304: Theft") 
            st.write("- Section 354: Assault")
            st.write("- Section 420: Fraud")
            st.write("- Section 506: Intimidation")
        
        with col2:
            st.write("**Common BNSS Sections:**")
            st.write("- Section 41: Arrest procedures")
            st.write("- Section 154: FIR registration")
            st.write("- Section 161: Examination of witnesses")
            st.write("- Section 173: Investigation reports")

def display_law_card(law, compact=False):
    """Display a law in a card format"""
    if not law:
        return
    
    # Extract law information
    section_id = law.get('section_id', 'N/A')
    title = law.get('title', 'Unknown')
    description = law.get('description', 'No description available')
    category = law.get('category', 'Unknown')
    
    # Color coding for law types
    type_colors = {
        'BNS': '#dc3545',    # Red for criminal law
        'BNSS': '#007bff',   # Blue for procedure
        'IPC': '#28a745',    # Green for old criminal law
        'CrPC': '#ffc107'    # Yellow for old procedure
    }
    
    type_color = type_colors.get(category, '#6c757d')
    
    # Create expandable card
    with st.expander(f"{title}", expanded=False):
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
            {category}
        </span>
        """, unsafe_allow_html=True)
        
        # Description
        st.write("**Description:**")
        st.write(description)
        
        # Action buttons for police officers
        current_user = st.session_state.get('user', {})
        if current_user and current_user.get('role') == 'police':
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"📋 Copy Reference", key=f"copy_{section_id}"):
                    reference_text = f"{title}"
                    st.success(f"Reference copied: {reference_text}")
            
            with col2:
                if st.button(f"📎 Add to Case Notes", key=f"add_notes_{section_id}"):
                    st.info(f"Legal reference '{title}' can be added to case notes when filing FIR or updating cases.")

def get_law_suggestions(complaint_text, category):
    """Get suggested laws based on complaint content"""
    suggestions = []
    
    # Simple keyword-based suggestions
    text_lower = complaint_text.lower()
    category_lower = category.lower()
    
    # Common law suggestions based on keywords
    if any(word in text_lower for word in ['murder', 'kill', 'death']):
        suggestions.append("BNS Section 103 - Murder")
    
    if any(word in text_lower for word in ['theft', 'steal', 'robbery']):
        suggestions.append("BNS Section 304 - Theft")
    
    if any(word in text_lower for word in ['assault', 'attack', 'violence']):
        suggestions.append("BNS Section 354 - Assault")
    
    if any(word in text_lower for word in ['fraud', 'cheat', 'scam']):
        suggestions.append("BNS Section 420 - Fraud")
    
    if any(word in text_lower for word in ['threat', 'intimidation', 'blackmail']):
        suggestions.append("BNS Section 506 - Intimidation")
    
    return suggestions

def display_law_suggestions(complaint_text, category):
    """Display suggested laws for a complaint"""
    suggestions = get_law_suggestions(complaint_text, category)
    
    if suggestions:
        st.subheader("💡 Suggested Legal References")
        st.info("Based on the complaint content, these laws might be applicable:")
        
        for suggestion in suggestions:
            st.write(f"• {suggestion}")
    
    return suggestions
