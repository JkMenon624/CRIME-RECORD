from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import os
from database import Database

# Initialize database
db = Database()

def generate_case_pdf(case_id, output_dir="case_pdfs"):
    """Generate PDF case file for a registered case"""
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get case details
    conn = db.connect()
    cursor = conn.cursor()
    
    # Get case and complaint data
    cursor.execute('''
        SELECT c.case_id, c.case_status, c.date_registered,
               comp.reference_number, comp.crime_type, comp.description, comp.location,
               comp.severity_level, comp.incident_date, comp.citizen_name, 
               comp.citizen_email, comp.citizen_phone,
               u.name as officer_name, u.badge_number
        FROM Cases c
        JOIN Complaints comp ON c.complaint_id = comp.complaint_id
        JOIN Users u ON c.police_officer_id = u.user_id
        WHERE c.case_id = ?
    ''', (case_id,))
    
    case_data = cursor.fetchone()
    
    if not case_data:
        conn.close()
        return None
    
    # Unpack case data
    (case_id, case_status, reg_date, comp_ref, crime_type, description, location,
     severity_level, incident_date, citizen_name, citizen_email, citizen_phone,
     officer_name, badge_number) = case_data
    
    # Create PDF filename
    pdf_filename = f"case_{comp_ref}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Header
    story.append(Paragraph("KERALA POLICE", title_style))
    story.append(Paragraph("CRIME RECORDS MANAGEMENT SYSTEM", styles['Normal']))
    story.append(Paragraph("CASE FILE REPORT", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Case Information Table
    case_info_data = [
        ['Reference Number:', comp_ref],
        ['Registration Date:', reg_date],
        ['Status:', case_status.upper()],
        ['Crime Type:', crime_type],
        ['Registering Officer:', f"{officer_name} (Badge: {badge_number})"],
        ['Severity Level:', severity_level]
    ]
    
    case_info_table = Table(case_info_data, colWidths=[2*inch, 4*inch])
    case_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    story.append(Paragraph("CASE INFORMATION", heading_style))
    story.append(case_info_table)
    story.append(Spacer(1, 20))
    
    # Complainant Information
    story.append(Paragraph("COMPLAINANT INFORMATION", heading_style))
    
    citizen_data = [
        ['Name:', citizen_name],
        ['Email:', citizen_email],
        ['Phone:', citizen_phone],
        ['Location:', location],
        ['Incident Date:', str(incident_date)]
    ]
    
    citizen_table = Table(citizen_data, colWidths=[2*inch, 4*inch])
    citizen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    story.append(citizen_table)
    story.append(Spacer(1, 15))
    
    # Incident Description
    story.append(Paragraph("INCIDENT DESCRIPTION", heading_style))
    story.append(Paragraph(description, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Case Updates
    cursor.execute('''
        SELECT cu.status, cu.notes, cu.update_date, cu.officer_badge
        FROM CaseUpdates cu
        JOIN Cases c ON cu.case_id = c.case_id
        WHERE c.case_id = ?
        ORDER BY cu.update_date DESC
    ''', (case_id,))
    
    updates = cursor.fetchall()
    
    if updates:
        story.append(Paragraph("CASE UPDATES", heading_style))
        
        for update in updates:
            status, notes, update_date, officer_badge = update
            story.append(Paragraph(f"<b>{update_date}</b> - Status: {status} (Officer: {officer_badge})", styles['Normal']))
            if notes:
                story.append(Paragraph(f"Notes: {notes}", styles['Normal']))
            story.append(Spacer(1, 10))
    
    # Legal References Section (placeholder for future enhancement)
    story.append(Paragraph("LEGAL REFERENCES", heading_style))
    story.append(Paragraph("Legal references and applicable laws will be added here based on case analysis.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("---", styles['Normal']))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph("Kerala Police Crime Records Management System", styles['Normal']))
    
    # Build PDF
    try:
        doc.build(story)
        
        # Update case record with PDF path
        cursor.execute('UPDATE Cases SET pdf_path = ? WHERE case_id = ?', (pdf_path, case_id))
        conn.commit()
        conn.close()
        
        return pdf_path
    except Exception as e:
        conn.close()
        raise Exception(f"Failed to generate PDF: {str(e)}")

def get_case_pdf_path(case_id):
    """Get the PDF path for a case if it exists"""
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute('SELECT pdf_path FROM Cases WHERE case_id = ?', (case_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] and os.path.exists(result[0]):
        return result[0]
    return None
