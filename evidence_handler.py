import os
import streamlit as st
import uuid
from pathlib import Path
import logging
from datetime import datetime

# Configure directories
EVIDENCE_DIR = "evidence_files"
ALLOWED_EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
    'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
    'audio': ['.mp3', '.wav', '.m4a', '.ogg', '.aac'],
    'video': ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.webm'],
    'other': ['.zip', '.rar', '.7z']
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def init_evidence_directory():
    """Create evidence directory if it doesn't exist"""
    Path(EVIDENCE_DIR).mkdir(exist_ok=True)
    return EVIDENCE_DIR

def get_file_type(filename):
    """Determine file type based on extension"""
    if not filename:
        return 'unknown'
    
    ext = Path(filename).suffix.lower()
    
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    
    return 'other'

def is_allowed_file(filename):
    """Check if file type is allowed"""
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower()
    all_allowed = []
    for extensions in ALLOWED_EXTENSIONS.values():
        all_allowed.extend(extensions)
    
    return ext in all_allowed

def save_uploaded_file(uploaded_file, complaint_id):
    """
    Save uploaded file to evidence directory with unique filename
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        complaint_id: ID of the complaint this evidence belongs to
    
    Returns:
        tuple: (success, file_path, error_message)
    """
    try:
        # Validate file
        if not uploaded_file:
            return False, None, "No file uploaded"
        
        if not is_allowed_file(uploaded_file.name):
            return False, None, f"File type not allowed. Allowed types: {', '.join([ext for exts in ALLOWED_EXTENSIONS.values() for ext in exts])}"
        
        if uploaded_file.size > MAX_FILE_SIZE:
            return False, None, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB"
        
        # Create evidence directory
        evidence_dir = init_evidence_directory()
        
        # Generate unique filename
        file_ext = Path(uploaded_file.name).suffix
        unique_filename = f"complaint_{complaint_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = os.path.join(evidence_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        logging.info(f"Evidence file saved: {file_path}")
        return True, file_path, None
        
    except Exception as e:
        error_msg = f"Error saving file: {str(e)}"
        logging.error(error_msg)
        return False, None, error_msg

def delete_evidence_file(file_path):
    """Delete evidence file from storage"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Evidence file deleted: {file_path}")
            return True
        else:
            logging.warning(f"Evidence file not found: {file_path}")
            return False
    except Exception as e:
        logging.error(f"Error deleting evidence file {file_path}: {str(e)}")
        return False

def get_file_size_readable(size_bytes):
    """Convert file size to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def display_evidence_list(evidence_list, show_actions=False, complaint_id=None, use_expander=True):
    """
    Display evidence files in a formatted list
    
    Args:
        evidence_list: List of evidence records from database
        show_actions: Whether to show action buttons (delete, etc.)
        complaint_id: Complaint ID for context
        use_expander: Whether to use expanders (set to False if already in an expander)
    """
    if not evidence_list:
        st.info("No evidence files uploaded for this complaint.")
        return
    
    st.subheader(f"📎 Evidence Files ({len(evidence_list)})")
    
    for evidence in evidence_list:
    # Use a styled container for each evidence item
        st.markdown(f"""
        <div style="
        border: 1px solid #e0e0e0; 
        border-radius: 8px; 
        padding: 15px; 
        margin: 10px 0;
        background-color: #f8f9fa;
     ">
        <h4 style="margin: 0; color: #1f77b4;">📄 {evidence.get('file_name', 'Unnamed File')}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Display evidence content
    display_evidence_content(evidence, show_actions=True)
    
    # Optional separator between evidence items
    st.markdown("---")

def display_evidence_content(evidence, show_actions):
    """Display the content of an evidence item"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**File Type:** {evidence['file_type'].title()}")
        st.write(f"**Size:** {get_file_size_readable(evidence.get('file_size', 0))}")
        st.write(f"**Uploaded:** {evidence['upload_date']}")
        st.write(f"**Uploaded by:** {evidence['uploaded_by']}")
    
    with col2:
        if evidence.get('description'):
            st.write(f"**Description:** {evidence['description']}")
        
        # File download button
        file_path = evidence['file_path']
        if os.path.exists(file_path):
            with open(file_path, "rb") as file:
                st.download_button(
                    label="📥 Download File",
                    data=file.read(),
                    file_name=evidence['file_name'],
                    mime=get_mime_type(evidence['file_type']),
                    key=f"download_{evidence['evidence_id']}"
                )
        else:
            st.error("⚠️ File not found on server")
    
    # Action buttons for authorized users
    if show_actions:
        if st.button(f"🗑️ Delete", key=f"delete_{evidence['evidence_id']}", type="secondary"):
            if delete_evidence_file(evidence['file_path']):
                from database import Database
                db = Database()
                if db.delete_evidence(evidence['evidence_id']):
                    st.success("Evidence file deleted successfully")
                    st.rerun()
                else:
                    st.error("Failed to delete evidence record from database")
            else:
                st.error("Failed to delete evidence file")

def get_mime_type(file_type):
    """Get MIME type for file download"""
    mime_types = {
        'image': 'image/*',
        'document': 'application/pdf',
        'audio': 'audio/*',
        'video': 'video/*',
        'other': 'application/octet-stream'
    }
    return mime_types.get(file_type, 'application/octet-stream')

def display_evidence_upload_form(complaint_id, user_email):
    """
    Display evidence upload form
    
    Args:
        complaint_id: ID of complaint to attach evidence to
        user_email: Email of user uploading evidence
    
    Returns:
        bool: True if file was uploaded successfully
    """
    from database import Database
    
    st.subheader("📎 Upload Evidence")
    
    with st.form(f"evidence_upload_{complaint_id}", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Choose evidence file",
            type=None,  # We'll validate manually
            help=f"Allowed types: Images, Documents (PDF, DOC), Audio, Video. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
        
        description = st.text_area(
            "Description (Optional)",
            placeholder="Describe what this evidence shows...",
            max_chars=500
        )
        
        submit_button = st.form_submit_button("📤 Upload Evidence", use_container_width=True)
        
        if submit_button and uploaded_file:
            # Save file
            success, file_path, error_msg = save_uploaded_file(uploaded_file, complaint_id)
            
            if success:
                # Add to database
                db = Database()
                file_type = get_file_type(uploaded_file.name)
                
                evidence_id = db.add_evidence(
                    complaint_id=complaint_id,
                    file_name=uploaded_file.name,
                    file_path=file_path,
                    file_type=file_type,
                    file_size=uploaded_file.size,
                    uploaded_by=user_email,
                    description=description
                )
                
                if evidence_id:
                    st.success(f"✅ Evidence uploaded successfully! File: {uploaded_file.name}")
                    return True
                else:
                    # Clean up file if database insertion failed
                    delete_evidence_file(file_path)
                    st.error("❌ Failed to save evidence record to database")
            else:
                st.error(f"❌ Upload failed: {error_msg}")
        
        elif submit_button and not uploaded_file:
            st.error("⚠️ Please select a file to upload")
    
    return False