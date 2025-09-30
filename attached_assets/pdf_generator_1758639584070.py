from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import os
from database import db

def generate_case_pdf(case_id, output_dir="case_pdfs"):
    """Generate PDF case file for a registered case"""
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get case details
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.case_number, c.registration_date, c.status, c.notes,
               comp.reference_number, comp.title, comp.description, comp.category, 
               comp.severity, comp.incident_date, comp.address, comp.district,
               comp.has_evidence, comp.has_witnesses,
               citizen.name as citizen_name, citizen.email as citizen_email, 
               citizen.phone as citizen_phone,
               officer.name as officer_name, officer.badge_number
        FROM cases c
        JOIN complaints comp ON c.complaint_id = comp.complaint_id
        JOIN users citizen ON comp.citizen_id = citizen.user_id
        JOIN users officer ON c.officer_id = officer.user_id
        WHERE c.case_id = ?
    ''', (case_id,))
    
    case_data = cursor.fetchone()
    
    if not case_data:
        conn.close()
        return None
    
    # Get associated laws
    cursor.execute('''
        SELECT l.law_type, l.section_number, l.title, l.description, l.punishment
        FROM case_laws cl
        JOIN laws l ON cl.law_id = l.law_id
        WHERE cl.case_id = ?
        ORDER BY l.law_type, l.section_number
    ''', (case_id,))
    
    laws = cursor.fetchall()
    conn.close()
    
    # Unpack case data
    (case_number, reg_date, status, notes, comp_ref, title, description, category, 
     severity, incident_date, address, district, has_evidence, has_witnesses,
     citizen_name, citizen_email, citizen_phone, officer_name, badge_number) = case_data
    
    # Create PDF filename
    pdf_filename = f"{case_number}_case_file.pdf"
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
        ['Case Number:', case_number],
        ['Registration Date:', reg_date],
        ['Status:', status.upper()],
        ['Complaint Reference:', comp_ref],
        ['Registering Officer:', f"{officer_name} (Badge: {badge_number})"],
        ['District:', district]
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
    
    # Complaint Details
    story.append(Paragraph("COMPLAINT DETAILS", heading_style))
    
    complaint_data = [
        ['Title:', title],
        ['Category:', category],
        ['Severity:', severity.upper()],
        ['Incident Date:', str(incident_date)],
        ['Evidence Available:', 'Yes' if has_evidence else 'No'],
        ['Witnesses Available:', 'Yes' if has_witnesses else 'No']
    ]
    
    complaint_table = Table(complaint_data, colWidths=[2*inch, 4*inch])
    complaint_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    story.append(complaint_table)
    story.append(Spacer(1, 15))
    
    # Citizen Information
    story.append(Paragraph("COMPLAINANT INFORMATION", heading_style))
    
    citizen_data = [
        ['Name:', citizen_name],
        ['Email:', citizen_email],
        ['Phone:', citizen_phone],
        ['Address:', address]
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
    
    # Officer Notes
    if notes:
        story.append(Paragraph("OFFICER NOTES", heading_style))
        story.append(Paragraph(notes, styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Legal References
    if laws:
        story.append(Paragraph("APPLICABLE LEGAL REFERENCES", heading_style))
        
        for law in laws:
            law_type, section_num, law_title, law_desc, punishment = law
            
            story.append(Paragraph(f"<b>{law_type} Section {section_num}: {law_title}</b>", styles['Normal']))
            story.append(Paragraph(law_desc, styles['Normal']))
            if punishment:
                story.append(Paragraph(f"<b>Punishment:</b> {punishment}", styles['Normal']))
            story.append(Spacer(1, 10))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("---", styles['Normal']))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph("Kerala Police Crime Records Management System", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    # Update case record with PDF path
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE cases SET pdf_path = ? WHERE case_id = ?', (pdf_path, case_id))
    conn.commit()
    conn.close()
    
    return pdf_path

def get_case_pdf_path(case_id):
    """Get the PDF path for a case if it exists"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT pdf_path FROM cases WHERE case_id = ?', (case_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] and os.path.exists(result[0]):
        return result[0]
    return None
