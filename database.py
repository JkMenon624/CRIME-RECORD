# database.py - SQLite operations
import sqlite3
from sqlite3 import Row
import os
import uuid
from datetime import datetime
import pandas as pd
import logging

logging.basicConfig(filename='crime_system.log', level=logging.ERROR)

class Database:
    def __init__(self, db_path="crime_records.db"):
        self.db_path = db_path

    def connect(self):
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = Row
            return conn
        except sqlite3.Error as e:
            raise Exception(f"Database connection failed: {str(e)}")

    def init_db(self):
        conn = self.connect()
        c = conn.cursor()
        
        # Users (add badge_number and department for officers)
        c.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT CHECK(role IN ('citizen','police')) DEFAULT 'citizen',
            email TEXT UNIQUE,
            phone TEXT,
            district TEXT,
            badge_number TEXT UNIQUE,
            department TEXT,
            password_hash TEXT
        );
        """)
        
        # Complaints (add fields from Streamlit app)
        c.execute("""
        CREATE TABLE IF NOT EXISTS Complaints (
            complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_number TEXT UNIQUE,
            user_id INTEGER,
            citizen_name TEXT,
            citizen_email TEXT,
            citizen_phone TEXT,
            crime_type TEXT,
            description TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            incident_date DATE,
            severity_level TEXT CHECK(severity_level IN ('Low','Medium','High')) DEFAULT 'Low',
            severity_score REAL,
            status TEXT CHECK(status IN ('Pending','Under Investigation','Resolved','Closed')) DEFAULT 'Pending',
            date_filed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_officer_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES Users(user_id),
            FOREIGN KEY(assigned_officer_id) REFERENCES Users(user_id)
        );
        """)
        
        # Cases (align case_status with app)
        c.execute("""
        CREATE TABLE IF NOT EXISTS Cases (
            case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            police_officer_id INTEGER,
            case_status TEXT CHECK(case_status IN ('Pending','Under Investigation','Resolved','Closed')) DEFAULT 'Pending',
            pdf_path TEXT,
            date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(complaint_id) REFERENCES Complaints(complaint_id),
            FOREIGN KEY(police_officer_id) REFERENCES Users(user_id)
        );
        """)
        
        # Case Updates (new table for case history)
        c.execute("""
        CREATE TABLE IF NOT EXISTS CaseUpdates (
            update_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            officer_badge TEXT,
            status TEXT CHECK(status IN ('Pending','Under Investigation','Resolved','Closed')),
            notes TEXT,
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(case_id) REFERENCES Cases(case_id)
        );
        """)
        
        # Case Legal References (link cases to applicable laws)
        c.execute("""
        CREATE TABLE IF NOT EXISTS CaseLegalReferences (
            reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            law_section_id INTEGER,
            added_by_officer TEXT,
            notes TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(case_id) REFERENCES Cases(case_id),
            FOREIGN KEY(law_section_id) REFERENCES Laws(section_id)
        );
        """)
        
        # Evidence table for storing uploaded files
        c.execute("""
        CREATE TABLE IF NOT EXISTS Evidence (
            evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            uploaded_by TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            FOREIGN KEY(complaint_id) REFERENCES Complaints(complaint_id)
        );
        """)
        
        # Laws (unchanged)
        c.execute("""
        CREATE TABLE IF NOT EXISTS Laws (
            section_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT
        );
        """)
        
        # Insert default police officer for testing
        try:
            c.execute("""
                INSERT OR IGNORE INTO Users (name, role, email, phone, district, password_hash, badge_number, department)
                VALUES ('Officer Kumar', 'police', 'officer@kerala.police.gov.in', '9876543210', 'Thiruvananthapuram', 
                        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'KP001', 'Crime Branch')
            """)
            # Password for above is 'password123'
        except sqlite3.IntegrityError:
            pass
        
        # Populate Laws table with essential BNS and BNSS sections
        essential_laws = [
            ("BNS Section 103 - Murder", "Whoever causes death by doing an act with the intention of causing death, or with the intention of causing such bodily injury as is likely to cause death, or with the knowledge that he is likely by such act to cause death, commits the offence of culpable homicide.", "BNS"),
            ("BNS Section 304 - Theft", "Whoever intends to take dishonestly any movable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft.", "BNS"),
            ("BNS Section 354 - Assault", "Whoever assaults or uses criminal force to any person, intending to outrage or knowing it to be likely that he will thereby outrage the modesty of that person, shall be punished with imprisonment of either description for a term which shall not be less than one year but which may extend to five years, and shall also be liable to fine.", "BNS"),
            ("BNS Section 420 - Fraud", "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, commits criminal breach of trust.", "BNS"),
            ("BNS Section 506 - Intimidation", "Whoever threatens another with any injury to his person, reputation or property, or to the person or reputation of any one in whom that person is interested, with intent to cause alarm to that person, or to cause that person to do any act which he is not legally bound to do, or to omit to do any act which that person is legally entitled to do, as the means of avoiding the execution of such threat, commits criminal intimidation.", "BNS"),
            ("BNSS Section 41 - Arrest Procedures", "Any police officer may without an order from a Magistrate and without a warrant, arrest any person who commits, in the presence of a police officer, a cognizable offence; or who has been concerned in any cognizable offence, or against whom a reasonable complaint has been made, or credible information has been received, or a reasonable suspicion exists, of his having been so concerned.", "BNSS"),
            ("BNSS Section 154 - FIR Registration", "Every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing by him or under his direction, and be read over to the informant; and every such information, whether given in writing or reduced to writing as aforesaid, shall be signed by the person giving it, and the substance thereof shall be entered in a book to be kept by such officer in such form as the State Government may prescribe in this behalf.", "BNSS"),
            ("BNSS Section 161 - Examination of Witnesses", "Any police officer making an investigation may examine orally any person supposed to be acquainted with the facts and circumstances of the case.", "BNSS"),
            ("BNSS Section 173 - Investigation Report", "Every investigation shall be completed without unnecessary delay. When the investigation has been completed, the officer in charge of the police station shall forward to a Magistrate empowered to take cognizance of the offence on a police report, a report in the prescribed form.", "BNSS"),
            ("BNS Section 143 - Rioting", "Whenever force or violence is used by an unlawful assembly, or by any member thereof, in prosecution of the common object of such assembly, every member of such assembly is guilty of the offence of rioting.", "BNS"),
            ("BNS Section 302 - Kidnapping", "Whoever conveys any person beyond the limits of India without the consent of that person, or of some person legally authorized to consent on behalf of that person, is said to kidnap that person from India.", "BNS"),
            ("BNS Section 120B - Criminal Conspiracy", "Whoever is a party to a criminal conspiracy to commit an offence punishable with death, imprisonment for life or rigorous imprisonment for a term of two years or upwards, shall, where no express provision is made in this Code for the punishment of such a conspiracy, be punished with the same punishment as if he had abetted such offence.", "BNS")
        ]
        
        for title, description, category in essential_laws:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO Laws (title, description, category)
                    VALUES (?, ?, ?)
                """, (title, description, category))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()

    # ---------- USERS ----------
    def create_user(self, name, email, phone, password_hash, role="citizen", district=None, badge_number=None, department=None):
        """Register a new user (default: citizen). Returns user_id or None if email exists."""
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO Users (name, role, email, phone, district, password_hash, badge_number, department)
                VALUES (?,?,?,?,?,?,?,?)
            """, (name, role, email, phone, district, password_hash, badge_number, department))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def authenticate_user(self, email, password_hash):
        """Authenticate a user by email + hashed password."""
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM Users WHERE email=? AND password_hash=?", (email, password_hash))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_email(self, email):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM Users WHERE email = ?", (email,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_badge(self, badge_number):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM Users WHERE badge_number = ?", (badge_number,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    # ---------- COMPLAINTS ----------
    def add_complaint(self, user_id, title, description, severity="Low"):
        conn = self.connect()
        c = conn.cursor()
        c.execute("INSERT INTO Complaints (user_id, crime_type, description, severity_level) VALUES (?,?,?,?)",
                  (user_id, title, description, severity))
        conn.commit()
        conn.close()

    def submit_complaint(self, complaint_data):
        """Submit a new complaint and return the reference number."""
        conn = self.connect()
        c = conn.cursor()
        
        # Generate unique reference number (e.g., CR202509230001)
        reference_number = f"CR{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
        
        try:
            c.execute("""
                INSERT INTO Complaints (
                    reference_number, citizen_name, citizen_email, citizen_phone, 
                    crime_type, description, location, latitude, longitude, 
                    incident_date, severity_level, severity_score, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                reference_number,
                complaint_data['citizen_name'],
                complaint_data['citizen_email'],
                complaint_data['citizen_phone'],
                complaint_data['crime_type'],
                complaint_data['description'],
                complaint_data['location'],
                complaint_data.get('latitude'),
                complaint_data.get('longitude'),
                complaint_data['incident_date'],
                complaint_data['severity_level'],
                complaint_data['severity_score'],
                'Pending'
            ))
            conn.commit()
            return reference_number
        except sqlite3.Error as e:
            logging.error(f"Failed to submit complaint: {str(e)}")
            raise Exception(f"Failed to submit complaint: {str(e)}")
        finally:
            conn.close()

    def get_pending_complaints(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
        SELECT * FROM Complaints 
        WHERE status = 'Pending'
        ORDER BY CASE severity_level WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 END, date_filed ASC
        """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    
    def search_complaints_advanced(self, search_query="", severity_filter="", location_filter="", 
                                 start_date=None, end_date=None, status_filter="", crime_type_filter="", 
                                 citizen_email=None, limit=None, offset=None):
        """Advanced search for complaints with multiple filters"""
        conn = self.connect()
        c = conn.cursor()
        
        where_clauses = []
        params = []
        
        # Text search across multiple fields
        if search_query:
            where_clauses.append("""
                (reference_number LIKE ? OR crime_type LIKE ? OR location LIKE ? 
                 OR description LIKE ? OR citizen_name LIKE ?)
            """)
            search_param = f'%{search_query}%'
            params.extend([search_param] * 5)
        
        # Severity filter
        if severity_filter and severity_filter != 'All':
            where_clauses.append("severity_level = ?")
            params.append(severity_filter)
        
        # Location filter
        if location_filter:
            where_clauses.append("location LIKE ?")
            params.append(f'%{location_filter}%')
        
        # Date range filter
        if start_date:
            where_clauses.append("DATE(date_filed) >= ?")
            params.append(start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            where_clauses.append("DATE(date_filed) <= ?")
            params.append(end_date.strftime('%Y-%m-%d'))
        
        # Status filter
        if status_filter and status_filter != 'All':
            where_clauses.append("status = ?")
            params.append(status_filter)
        
        # Crime type filter
        if crime_type_filter and crime_type_filter != 'All':
            where_clauses.append("crime_type = ?")
            params.append(crime_type_filter)
        
        # Citizen email filter (for citizen-specific searches)
        if citizen_email:
            where_clauses.append("citizen_email = ?")
            params.append(citizen_email)
        
        # Build query
        query = """
            SELECT c.*, u.name AS assigned_officer 
            FROM Complaints c 
            LEFT JOIN Users u ON c.assigned_officer_id = u.user_id
        """
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY date_filed DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
        
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    
    def count_complaints_advanced(self, search_query="", severity_filter="", location_filter="", 
                                start_date=None, end_date=None, status_filter="", crime_type_filter="", 
                                citizen_email=None):
        """Count complaints matching advanced search filters"""
        conn = self.connect()
        c = conn.cursor()
        
        where_clauses = []
        params = []
        
        # Text search across multiple fields
        if search_query:
            where_clauses.append("""
                (reference_number LIKE ? OR crime_type LIKE ? OR location LIKE ? 
                 OR description LIKE ? OR citizen_name LIKE ?)
            """)
            search_param = f'%{search_query}%'
            params.extend([search_param] * 5)
        
        # Severity filter
        if severity_filter and severity_filter != 'All':
            where_clauses.append("severity_level = ?")
            params.append(severity_filter)
        
        # Location filter
        if location_filter:
            where_clauses.append("location LIKE ?")
            params.append(f'%{location_filter}%')
        
        # Date range filter
        if start_date:
            where_clauses.append("DATE(date_filed) >= ?")
            params.append(start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            where_clauses.append("DATE(date_filed) <= ?")
            params.append(end_date.strftime('%Y-%m-%d'))
        
        # Status filter
        if status_filter and status_filter != 'All':
            where_clauses.append("status = ?")
            params.append(status_filter)
        
        # Crime type filter
        if crime_type_filter and crime_type_filter != 'All':
            where_clauses.append("crime_type = ?")
            params.append(crime_type_filter)
        
        # Citizen email filter (for citizen-specific searches)
        if citizen_email:
            where_clauses.append("citizen_email = ?")
            params.append(citizen_email)
        
        # Build count query
        query = "SELECT COUNT(*) as count FROM Complaints"
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        c.execute(query, params)
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def get_complaint_statistics(self):
        """Get comprehensive complaint statistics"""
        conn = self.connect()
        c = conn.cursor()
        
        # Get crime types
        c.execute("SELECT DISTINCT crime_type FROM Complaints ORDER BY crime_type")
        crime_types = [row[0] for row in c.fetchall()]
        
        # Get locations
        c.execute("SELECT DISTINCT location FROM Complaints ORDER BY location")
        locations = [row[0] for row in c.fetchall()]
        
        # Get status counts
        c.execute("""
            SELECT status, COUNT(*) as count 
            FROM Complaints 
            GROUP BY status
        """)
        status_counts = dict(c.fetchall())
        
        # Get severity counts
        c.execute("""
            SELECT severity_level, COUNT(*) as count 
            FROM Complaints 
            GROUP BY severity_level
        """)
        severity_counts = dict(c.fetchall())
        
        # Get monthly complaint trends
        c.execute("""
            SELECT strftime('%Y-%m', date_filed) as month, COUNT(*) as count
            FROM Complaints 
            GROUP BY strftime('%Y-%m', date_filed)
            ORDER BY month DESC
            LIMIT 12
        """)
        monthly_trends = dict(c.fetchall())
        
        conn.close()
        
        return {
            'crime_types': crime_types,
            'locations': locations,
            'status_counts': status_counts,
            'severity_counts': severity_counts,
            'monthly_trends': monthly_trends
        }
    
    def add_evidence(self, complaint_id, file_name, file_path, file_type, file_size, uploaded_by, description=""):
        """Add evidence file record to the database"""
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO Evidence (complaint_id, file_name, file_path, file_type, file_size, uploaded_by, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (complaint_id, file_name, file_path, file_type, file_size, uploaded_by, description))
            conn.commit()
            evidence_id = c.lastrowid
            return evidence_id
        except sqlite3.Error as e:
            logging.error(f"Failed to add evidence: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_evidence_by_complaint(self, complaint_id):
        """Get all evidence for a specific complaint"""
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM Evidence 
            WHERE complaint_id = ? 
            ORDER BY upload_date DESC
        """, (complaint_id,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    
    def delete_evidence(self, evidence_id):
        """Delete evidence record from database"""
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM Evidence WHERE evidence_id = ?", (evidence_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Failed to delete evidence: {str(e)}")
            return False
        finally:
            conn.close()

    def get_complaints(self, officer=None):
        """Retrieve all complaints or those assigned to a specific officer."""
        conn = self.connect()
        c = conn.cursor()
        if officer:
            c.execute("""
                SELECT c.*, u.name AS assigned_officer 
                FROM Complaints c 
                LEFT JOIN Users u ON c.assigned_officer_id = u.user_id 
                WHERE c.assigned_officer_id = (SELECT user_id FROM Users WHERE badge_number = ?)
            """, (officer,))
        else:
            c.execute("""
                SELECT c.*, u.name AS assigned_officer 
                FROM Complaints c 
                LEFT JOIN Users u ON c.assigned_officer_id = u.user_id
            """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return pd.DataFrame(rows)

    def get_complaint_by_reference(self, reference_number):
        """Retrieve a complaint by its reference number."""
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT c.*, u.name AS assigned_officer 
            FROM Complaints c 
            LEFT JOIN Users u ON c.assigned_officer_id = u.user_id 
            WHERE c.reference_number = ?
        """, (reference_number,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def mark_complaint_registered(self, complaint_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("UPDATE Complaints SET status = 'Under Investigation' WHERE complaint_id = ?", (complaint_id,))
        conn.commit()
        conn.close()

    def update_complaint_status(self, complaint_id, new_status, officer_badge, notes):
        """Update complaint status and add to case updates."""
        conn = self.connect()
        c = conn.cursor()
        try:
            # Update complaint status
            c.execute("UPDATE Complaints SET status = ? WHERE complaint_id = ?", (new_status, complaint_id))
            
            # Get or create case_id
            c.execute("SELECT case_id FROM Cases WHERE complaint_id = ?", (complaint_id,))
            case = c.fetchone()
            officer_id = None
            officer_row = self.get_user_by_badge(officer_badge)
            if officer_row:
                officer_id = officer_row['user_id']
            
            if not case:
                c.execute("INSERT INTO Cases (complaint_id, police_officer_id, case_status) VALUES (?,?,?)", 
                          (complaint_id, officer_id, new_status))
                case_id = c.lastrowid
            else:
                case_id = case['case_id']
                c.execute("UPDATE Cases SET case_status = ?, police_officer_id = ? WHERE case_id = ?", (new_status, officer_id, case_id))
            
            # Add case update
            c.execute("""
                INSERT INTO CaseUpdates (case_id, officer_badge, status, notes) 
                VALUES (?,?,?,?)
            """, (case_id, officer_badge, new_status, notes))
            
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to update complaint status: {str(e)}")
            raise Exception(f"Failed to update complaint status: {str(e)}")
        finally:
            conn.close()

    # ---------- CASES ----------
    def register_case(self, complaint_id, police_officer_id, pdf_path):
        conn = self.connect()
        c = conn.cursor()
        c.execute("INSERT INTO Cases (complaint_id, police_officer_id, pdf_path, case_status) VALUES (?,?,?,?)",
                  (complaint_id, police_officer_id, pdf_path, 'Under Investigation'))
        conn.commit()
        self.mark_complaint_registered(complaint_id)
        conn.close()

    def get_case_updates(self, complaint_id):
        """Retrieve case updates for a complaint."""
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT cu.* 
            FROM CaseUpdates cu 
            JOIN Cases c ON cu.case_id = c.case_id 
            WHERE c.complaint_id = ?
            ORDER BY cu.update_date DESC
        """, (complaint_id,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return pd.DataFrame(rows)

    # ---------- LAWS ----------
    def add_law(self, title, description, category):
        conn = self.connect()
        c = conn.cursor()
        c.execute("INSERT INTO Laws (title, description, category) VALUES (?,?,?)",
                  (title, description, category))
        conn.commit()
        conn.close()

    def get_laws(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM Laws ORDER BY title")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def search_laws(self, query, law_type=""):
        """Search laws with query and optional type filter"""
        conn = self.connect()
        c = conn.cursor()
        
        if query:
            # Search in title, description, and category
            if law_type:
                c.execute("""
                    SELECT * FROM Laws 
                    WHERE category = ? AND (
                        title LIKE ? OR description LIKE ? OR category LIKE ?
                    )
                    ORDER BY title
                """, (law_type, f'%{query}%', f'%{query}%', f'%{query}%'))
            else:
                c.execute("""
                    SELECT * FROM Laws 
                    WHERE title LIKE ? OR description LIKE ? OR category LIKE ?
                    ORDER BY category, title
                """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        else:
            # Return all laws of type if no query
            if law_type:
                c.execute("SELECT * FROM Laws WHERE category = ? ORDER BY title", (law_type,))
            else:
                c.execute("SELECT * FROM Laws ORDER BY category, title")
        
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def add_case_legal_reference(self, case_id, law_section_id, officer_badge, notes=""):
        """Add a legal reference to a case"""
        conn = self.connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO CaseLegalReferences (case_id, law_section_id, added_by_officer, notes)
                VALUES (?, ?, ?, ?)
            """, (case_id, law_section_id, officer_badge, notes))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Failed to add legal reference: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_case_legal_references(self, case_id):
        """Get legal references for a case"""
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT clr.*, l.title, l.description, l.category
            FROM CaseLegalReferences clr
            JOIN Laws l ON clr.law_section_id = l.section_id
            WHERE clr.case_id = ?
            ORDER BY clr.date_added DESC
        """, (case_id,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_connection(self):
        """Get database connection for direct queries"""
        return self.connect()
