import sqlite3
from typing import Optional, List, Dict, Any


def _connect(db_path: str) -> sqlite3.Connection:
	conn = sqlite3.connect(db_path, check_same_thread=False)
	conn.row_factory = sqlite3.Row
	return conn


def init_db(db_path: str) -> None:
	conn = _connect(db_path)
	cur = conn.cursor()
	# users
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS users (
			user_id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			email TEXT UNIQUE,
			password_hash TEXT DEFAULT '',
			role TEXT DEFAULT 'citizen'
		);
		"""
	)
	# complaints
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS complaints (
			complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id INTEGER,
			title TEXT NOT NULL,
			description TEXT NOT NULL,
			severity TEXT NOT NULL,
			status TEXT DEFAULT 'pending',
			date_filed TEXT NOT NULL,
			FOREIGN KEY(user_id) REFERENCES users(user_id)
		);
		"""
	)
	# cases (registered from complaints)
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS cases (
			case_id INTEGER PRIMARY KEY AUTOINCREMENT,
			complaint_id INTEGER NOT NULL,
			police_officer_id INTEGER NOT NULL,
			registered_at TEXT NOT NULL,
			pdf_path TEXT,
			FOREIGN KEY(complaint_id) REFERENCES complaints(complaint_id),
			FOREIGN KEY(police_officer_id) REFERENCES users(user_id)
		);
		"""
	)
	# laws reference
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS laws (
			law_id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			description TEXT NOT NULL,
			category TEXT NOT NULL
		);
		"""
	)
	conn.commit()
	conn.close()


def create_user(db_path: str, name: str, email: Optional[str], password: str, role: str = "citizen") -> int:
	from auth import hash_password  # local import to avoid cycle during boot
	conn = _connect(db_path)
	cur = conn.cursor()
	password_hash = hash_password(password) if password else ""
	cur.execute(
		"INSERT INTO users(name, email, password_hash, role) VALUES(?, ?, ?, ?)",
		(name, email, password_hash, role),
	)
	conn.commit()
	user_id = cur.lastrowid
	conn.close()
	return user_id


def get_user_by_email(db_path: str, email: str) -> Optional[Dict[str, Any]]:
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute("SELECT * FROM users WHERE email = ?", (email,))
	row = cur.fetchone()
	conn.close()
	return dict(row) if row else None


def add_complaint(db_path: str, user_id: Optional[int], title: str, description: str, severity: str) -> int:
	from datetime import datetime
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute(
		"""
		INSERT INTO complaints(user_id, title, description, severity, status, date_filed)
		VALUES(?, ?, ?, ?, 'pending', ?)
		""",
		(user_id, title, description, severity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
	)
	conn.commit()
	complaint_id = cur.lastrowid
	conn.close()
	return complaint_id


def get_pending_complaints(db_path: str) -> List[Dict[str, Any]]:
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute(
		"""
		SELECT * FROM complaints
		WHERE status = 'pending'
		ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, date_filed DESC
		"""
	)
	rows = [dict(r) for r in cur.fetchall()]
	conn.close()
	return rows


def register_case(db_path: str, complaint_id: int, police_officer_id: int, pdf_path: Optional[str]) -> int:
	from datetime import datetime
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute(
		"INSERT INTO cases(complaint_id, police_officer_id, registered_at, pdf_path) VALUES(?, ?, ?, ?)",
		(complaint_id, police_officer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pdf_path),
	)
	cur.execute("UPDATE complaints SET status = 'registered' WHERE complaint_id = ?", (complaint_id,))
	conn.commit()
	case_id = cur.lastrowid
	conn.close()
	return case_id


def get_complaints_for_officer(db_path: str, officer_id: int) -> List[Dict[str, Any]]:
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute(
		"""
		SELECT c.* FROM complaints c
		JOIN cases k ON k.complaint_id = c.complaint_id
		WHERE k.police_officer_id = ?
		ORDER BY c.date_filed DESC
		""",
		(officer_id,),
	)
	rows = [dict(r) for r in cur.fetchall()]
	conn.close()
	return rows


def insert_law(db_path: str, title: str, description: str, category: str) -> int:
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute(
		"INSERT INTO laws(title, description, category) VALUES(?, ?, ?)",
		(title, description, category),
	)
	conn.commit()
	law_id = cur.lastrowid
	conn.close()
	return law_id


def get_all_laws(db_path: str) -> List[Dict[str, Any]]:
	conn = _connect(db_path)
	cur = conn.cursor()
	cur.execute("SELECT * FROM laws ORDER BY category, title")
	rows = [dict(r) for r in cur.fetchall()]
	conn.close()
	return rows
