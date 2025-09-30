import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import json
import time
from urllib.parse import urljoin, urlparse
import logging
from typing import Dict, List, Optional
import os
import PyPDF2
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndianLegalDocumentScraper:
    def __init__(self, db_path: str = "indian_legal_documents.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.init_database()
        
        # Official sources for Indian legal documents
        self.sources = {
            'BNS': {
                'name': 'Bharatiya Nyaya Sanhita',
                'urls': [
                    'https://prsindia.org/files/bills_acts/bills_parliament/2023/Bharatiya%20Nyaya%20Sanhita,%202023.pdf',
                    'https://legislative.gov.in/sites/default/files/A2023-45.pdf'
                ]
            },
            'BNSS': {
                'name': 'Bharatiya Nagarik Suraksha Sanhita',
                'urls': [
                    'https://prsindia.org/files/bills_acts/bills_parliament/2023/Bharatiya%20Nagrik%20Suraksha%20Sanhita,%202023.pdf',
                    'https://legislative.gov.in/sites/default/files/A2023-46.pdf'
                ]
            },
            'Constitution': {
                'name': 'Constitution of India',
                'urls': [
                    'https://cdnbbsr.s3waas.gov.in/s380537a945c7aaa788ccfcdf1b99b5d8f/uploads/2023/05/Constitution-of-India.pdf',
                    'https://www.india.gov.in/sites/upload_files/npi/files/coi_part_full.pdf'
                ]
            }
        }
    
    def init_database(self):
        """Initialize SQLite database with tables for Indian legal documents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create main documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                document_type TEXT NOT NULL,
                title TEXT,
                url TEXT,
                full_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create sections table (for BNS and BNSS sections, Constitution articles)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                section_number TEXT,
                chapter_number TEXT,
                title TEXT,
                content TEXT,
                section_type TEXT, -- 'section', 'article', 'schedule', 'part'
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        # Create chapters table (for organizing sections)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                chapter_number TEXT,
                title TEXT,
                description TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        # Create keywords table for search functionality
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                keyword TEXT,
                relevance_score REAL,
                FOREIGN KEY (section_id) REFERENCES sections (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def fetch_pdf_content(self, url: str) -> Optional[str]:
        """Fetch and extract text from PDF"""
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            return text_content
        except Exception as e:
            logger.error(f"Error fetching PDF from {url}: {e}")
            return None
    
    def fetch_web_content(self, url: str) -> Optional[str]:
        """Fetch content from web page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            return soup.get_text()
        except Exception as e:
            logger.error(f"Error fetching web content from {url}: {e}")
            return None
    
    def parse_bns_content(self, content: str, document_id: int):
        """Parse BNS content and extract sections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pattern to match BNS sections
        section_pattern = r'(\d+)\.\s*([^\n]+)\n(.*?)(?=\n\d+\.\s*[^\n]+|\nCHAPTER|\n$)'
        chapter_pattern = r'CHAPTER\s*([IVX]+)\s*([^\n]+)'
        
        # Extract chapters
        chapters = re.findall(chapter_pattern, content, re.IGNORECASE)
        for chapter_num, chapter_title in chapters:
            cursor.execute('''
                INSERT INTO chapters (document_id, chapter_number, title)
                VALUES (?, ?, ?)
            ''', (document_id, chapter_num.strip(), chapter_title.strip()))
        
        # Extract sections
        sections = re.findall(section_pattern, content, re.DOTALL)
        for section_num, section_title, section_content in sections:
            cursor.execute('''
                INSERT INTO sections (document_id, section_number, title, content, section_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (document_id, section_num, section_title.strip(), section_content.strip(), 'section'))
            
            section_id = cursor.lastrowid
            self.extract_keywords(section_id, section_title + " " + section_content, cursor)
        
        conn.commit()
        conn.close()
        logger.info(f"Parsed {len(sections)} sections from BNS")
    
    def parse_bnss_content(self, content: str, document_id: int):
        """Parse BNSS content and extract sections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Similar pattern for BNSS
        section_pattern = r'(\d+)\.\s*([^\n]+)\n(.*?)(?=\n\d+\.\s*[^\n]+|\nCHAPTER|\n$)'
        chapter_pattern = r'CHAPTER\s*([IVX]+)\s*([^\n]+)'
        
        # Extract chapters
        chapters = re.findall(chapter_pattern, content, re.IGNORECASE)
        for chapter_num, chapter_title in chapters:
            cursor.execute('''
                INSERT INTO chapters (document_id, chapter_number, title)
                VALUES (?, ?, ?)
            ''', (document_id, chapter_num.strip(), chapter_title.strip()))
        
        # Extract sections
        sections = re.findall(section_pattern, content, re.DOTALL)
        for section_num, section_title, section_content in sections:
            cursor.execute('''
                INSERT INTO sections (document_id, section_number, title, content, section_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (document_id, section_num, section_title.strip(), section_content.strip(), 'section'))
            
            section_id = cursor.lastrowid
            self.extract_keywords(section_id, section_title + " " + section_content, cursor)
        
        conn.commit()
        conn.close()
        logger.info(f"Parsed {len(sections)} sections from BNSS")
    
    def parse_constitution_content(self, content: str, document_id: int):
        """Parse Constitution content and extract articles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Patterns for Constitution
        article_pattern = r'Article\s*(\d+[A-Z]*)\.\s*([^\n]+)\n(.*?)(?=\nArticle\s*\d+|\nPART|\n$)'
        part_pattern = r'PART\s*([IVX]+[A-Z]*)\s*([^\n]+)'
        schedule_pattern = r'SCHEDULE\s*([IVX]*)\s*([^\n]+)\n(.*?)(?=\nSCHEDULE|\n$)'
        
        # Extract parts
        parts = re.findall(part_pattern, content, re.IGNORECASE)
        for part_num, part_title in parts:
            cursor.execute('''
                INSERT INTO chapters (document_id, chapter_number, title, description)
                VALUES (?, ?, ?, ?)
            ''', (document_id, part_num.strip(), part_title.strip(), 'Constitutional Part'))
        
        # Extract articles
        articles = re.findall(article_pattern, content, re.DOTALL)
        for article_num, article_title, article_content in articles:
            cursor.execute('''
                INSERT INTO sections (document_id, section_number, title, content, section_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (document_id, article_num, article_title.strip(), article_content.strip(), 'article'))
            
            section_id = cursor.lastrowid
            self.extract_keywords(section_id, article_title + " " + article_content, cursor)
        
        # Extract schedules
        schedules = re.findall(schedule_pattern, content, re.DOTALL)
        for schedule_num, schedule_title, schedule_content in schedules:
            cursor.execute('''
                INSERT INTO sections (document_id, section_number, title, content, section_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (document_id, schedule_num or 'N/A', schedule_title.strip(), schedule_content.strip(), 'schedule'))
            
            section_id = cursor.lastrowid
            self.extract_keywords(section_id, schedule_title + " " + schedule_content, cursor)
        
        conn.commit()
        conn.close()
        logger.info(f"Parsed {len(articles)} articles and {len(schedules)} schedules from Constitution")
    
    def extract_keywords(self, section_id: int, text: str, cursor):
        """Extract keywords from text for search indexing"""
        # Simple keyword extraction - can be enhanced with NLP libraries
        import string
        
        # Remove punctuation and convert to lowercase
        text = text.translate(str.maketrans('', '', string.punctuation)).lower()
        words = text.split()
        
        # Filter common words and extract meaningful keywords
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'shall', 'be', 'is', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'cannot', 'such', 'any', 'every', 'all', 'some', 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'now', 'here', 'there', 'where', 'when', 'while', 'how', 'what', 'which', 'who', 'whom', 'whose', 'why', 'this', 'that', 'these', 'those', 'him', 'her', 'his', 'hers', 'its', 'their', 'theirs', 'our', 'ours', 'your', 'yours', 'my', 'mine', 'me', 'us', 'them', 'he', 'she', 'it', 'we', 'you', 'they', 'i'}
        
        # Get word frequency
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Insert top keywords
        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]:
            relevance_score = freq / len(words)
            cursor.execute('''
                INSERT INTO keywords (section_id, keyword, relevance_score)
                VALUES (?, ?, ?)
            ''', (section_id, word, relevance_score))
    
    def scrape_document(self, doc_type: str) -> bool:
        """Scrape a specific document type"""
        if doc_type not in self.sources:
            logger.error(f"Unknown document type: {doc_type}")
            return False
        
        doc_info = self.sources[doc_type]
        content = None
        successful_url = None
        
        # Try each URL until one works
        for url in doc_info['urls']:
            logger.info(f"Attempting to fetch {doc_type} from {url}")
            
            if url.endswith('.pdf'):
                content = self.fetch_pdf_content(url)
            else:
                content = self.fetch_web_content(url)
            
            if content:
                successful_url = url
                break
            
            time.sleep(2)  # Be respectful to servers
        
        if not content:
            logger.error(f"Failed to fetch content for {doc_type}")
            return False
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documents (source, document_type, title, url, full_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (doc_type, doc_type, doc_info['name'], successful_url, content))
        
        document_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Parse content based on document type
        if doc_type == 'BNS':
            self.parse_bns_content(content, document_id)
        elif doc_type == 'BNSS':
            self.parse_bnss_content(content, document_id)
        elif doc_type == 'Constitution':
            self.parse_constitution_content(content, document_id)
        
        logger.info(f"Successfully processed {doc_type}")
        return True
    
    def scrape_all_documents(self):
        """Scrape all Indian legal documents"""
        logger.info("Starting to scrape Indian legal documents...")
        
        success_count = 0
        for doc_type in self.sources.keys():
            if self.scrape_document(doc_type):
                success_count += 1
            time.sleep(5)  # Respectful delay between documents
        
        logger.info(f"Completed scraping. Successfully processed {success_count}/{len(self.sources)} documents")
        return success_count == len(self.sources)
    
    def search_database(self, query: str, limit: int = 10) -> List[Dict]:
        """Search the database for relevant sections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Search in section titles and content
        cursor.execute('''
            SELECT s.id, d.document_type, s.section_number, s.title, s.content, s.section_type
            FROM sections s
            JOIN documents d ON s.document_id = d.id
            WHERE s.title LIKE ? OR s.content LIKE ?
            ORDER BY 
                CASE 
                    WHEN s.title LIKE ? THEN 1
                    WHEN s.content LIKE ? THEN 2
                    ELSE 3
                END
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'document_type': row[1],
                'section_number': row[2],
                'title': row[3],
                'content': row[4][:200] + '...' if len(row[4]) > 200 else row[4],
                'section_type': row[5]
            })
        
        conn.close()
        return results
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Document counts
        cursor.execute('SELECT document_type, COUNT(*) FROM documents GROUP BY document_type')
        stats['documents'] = dict(cursor.fetchall())
        
        # Section counts
        cursor.execute('SELECT d.document_type, COUNT(*) FROM sections s JOIN documents d ON s.document_id = d.id GROUP BY d.document_type')
        stats['sections'] = dict(cursor.fetchall())
        
        # Total keywords
        cursor.execute('SELECT COUNT(*) FROM keywords')
        stats['total_keywords'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

def main():
    """Main function to run the scraper"""
    scraper = IndianLegalDocumentScraper()
    
    # Scrape all documents
    success = scraper.scrape_all_documents()
    
    if success:
        print("Database creation completed successfully!")
        
        # Show statistics
        stats = scraper.get_statistics()
        print("\nDatabase Statistics:")
        print(f"Documents: {stats['documents']}")
        print(f"Sections: {stats['sections']}")
        print(f"Total Keywords: {stats['total_keywords']}")
        
        # Example search
        print("\nExample search for 'murder':")
        results = scraper.search_database('murder', 5)
        for result in results:
            print(f"- {result['document_type']} Section {result['section_number']}: {result['title']}")
    else:
        print("Some documents could not be processed. Check logs for details.")

if __name__ == "__main__":
    main()
    