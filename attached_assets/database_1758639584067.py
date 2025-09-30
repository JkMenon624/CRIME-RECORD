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
        
        # Laws (unchanged)
        c.execute("""
        CREATE TABLE IF NOT EXISTS Laws (
            section_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT
        );
        """)
        
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
        c.execute("UPDATE Complaints SET status = 'registered' WHERE complaint_id = ?", (complaint_id,))
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
        c.execute("INSERT INTO Cases (complaint_id, police_officer_id, pdf_path) VALUES (?,?,?)",
                  (complaint_id, police_officer_id, pdf_path))
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

    def get_all_laws(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM Laws ORDER BY section_id ASC")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    # ---------- STATISTICS ----------
    def get_statistics(self):
        """Return basic statistics for dashboard/homepage"""
        conn = self.connect()
        c = conn.cursor()

        stats = {}

        c.execute("SELECT COUNT(*) FROM Users")
        stats["total_users"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM Complaints")
        stats["total_complaints"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'Pending'")
        stats["pending_complaints"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'registered'")
        stats["registered_complaints"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM Cases")
        stats["total_cases"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM Cases WHERE case_status = 'Pending'")
        stats["open_cases"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM Laws")
        stats["total_laws"] = c.fetchone()[0]

        conn.close()
        return stats

    def get_crime_stats(self):
        """Enhanced statistics for the public dashboard."""
        conn = self.connect()
        c = conn.cursor()
        
        stats = {}
        
        c.execute("SELECT COUNT(*) FROM Complaints")
        stats["total_cases"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM Complaints WHERE status IN ('Pending', 'Under Investigation')")
        stats["open_cases"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM Complaints WHERE status = 'Resolved'")
        stats["resolved_cases"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM Complaints WHERE severity_level = 'High'")
        stats["high_severity_cases"] = c.fetchone()[0]
        
        conn.close()
        return stats


# ✅ Create a global db instance
db = Database()