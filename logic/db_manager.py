import mysql.connector
import bcrypt
import json
from config.settings import DB_CONFIG
import logging
from datetime import datetime
import base64 # FIX 2: Added for content obfuscation

# Configure logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _get_db_connection():
    """Establishes and returns a database connection."""
    conn = None
    try:
        # NOTE: DB_CONFIG must contain user, password, host, database keys
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            logging.info("Database connection successfully established.")
            return conn
    except mysql.connector.Error as e:
        logging.error(f"Failed to connect to MySQL database: {e}")
        return None

# --- User Authentication Functions (Unchanged) ---

def register_user(username, password):
    """Registers a new user with a hashed password."""
    conn = None
    try:
        conn = _get_db_connection()
        if not conn:
            return False, "Database connection failed."

        cursor = conn.cursor()
        
        # Hash the password (CRITICAL SECURITY STEP)
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        insert_query = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
        cursor.execute(insert_query, (username, hashed_password))
        conn.commit()
        logging.info(f"User '{username}' registered successfully.")
        return True, "Registration successful! Please log in."
        
    except mysql.connector.Error as e:
        if "Duplicate entry" in str(e):
            return False, "Username already exists. Please choose another."
        logging.error(f"Error during registration: {e}")
        return False, f"Registration failed: {e}"
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def authenticate_user(username, password):
    """Authenticates a user and returns their user_id on success."""
    conn = None
    try:
        conn = _get_db_connection()
        if not conn:
            return False, "Database connection failed.", None

        cursor = conn.cursor()
        select_query = "SELECT user_id, password_hash FROM users WHERE username = %s"
        cursor.execute(select_query, (username,))
        result = cursor.fetchone()

        if result:
            user_id = result[0]
            stored_password_hash = result[1].encode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash):
                logging.info(f"User '{username}' authenticated.")
                return True, "Login successful!", user_id
            else:
                logging.warning(f"Authentication failed for '{username}': Invalid password.")
                return False, "Invalid username or password.", None
        else:
            logging.warning(f"Authentication failed: User '{username}' not found.")
            return False, "Invalid username or password.", None
            
    except mysql.connector.Error as e:
        logging.error(f"Error during authentication: {e}")
        return False, f"Login failed due to DB error: {e}", None
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- Document Management Functions ---

def _execute_query(query, params=None, fetch=False, fetchone=False):
    """Helper to handle connection, cursor, execution, and closing."""
    conn = _get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True) # Return results as dictionaries
        cursor.execute(query, params or ())
        
        if fetchone:
            result = cursor.fetchone()
            return result
        elif fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return cursor.lastrowid if 'INSERT' in query.upper() else True
            
    except mysql.connector.Error as e:
        # **CRITICAL DEBUGGING CHANGE: Log the specific error and re-raise**
        logging.error(f"Database operation failed: {e}. Query: {query.strip()[:100]}...")
        raise mysql.connector.Error(f"DB Query Failed: {e}") 
        
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def _decode_document_fields(document):
    """Helper function to decode Base64 fields after fetching."""
    if document and document.get('content'):
        try:
            # Decode content
            document['content'] = base64.b64decode(document['content']).decode('utf-8')
            # Decode syllabus
            document['syllabus_used'] = base64.b64decode(document['syllabus_used']).decode('utf-8')
        except Exception as e:
            logging.error(f"Content decoding failed for document {document.get('doc_id')}: {e}")
            document['content'] = f"DECODING ERROR: Could not decode document content."
            document['syllabus_used'] = f"DECODING ERROR: Could not decode syllabus."
    return document

def insert_document(user_id, doc_title, doc_type, syllabus_used, content, generation_params):
    """Inserts a new document record, encoding content."""
    
    # --- START OBFUSCATION ---
    try:
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        encoded_syllabus = base64.b64encode(syllabus_used.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logging.error(f"Content encoding failed during insert: {e}")
        return None
    # --- END OBFUSCATION ---
    
    query = """
    INSERT INTO course_documents 
    (user_id, doc_title, doc_type, syllabus_used, content, generation_params) 
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (user_id, doc_title, doc_type, encoded_syllabus, encoded_content, generation_params)
    
    try:
        return _execute_query(query, params)
    except mysql.connector.Error:
        return None # Return None on DB error, which triggers the messagebox

def update_document(doc_id, doc_title, doc_type, syllabus_used, content, generation_params):
    """Updates an existing document record, encoding content."""
    
    # --- START OBFUSCATION ---
    try:
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        encoded_syllabus = base64.b64encode(syllabus_used.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logging.error(f"Content encoding failed during update: {e}")
        return None
    # --- END OBFUSCATION ---
    
    query = """
    UPDATE course_documents SET
    doc_title = %s, doc_type = %s, syllabus_used = %s, content = %s, 
    generation_params = %s, date_generated = NOW()
    WHERE doc_id = %s
    """
    params = (doc_title, doc_type, encoded_syllabus, encoded_content, generation_params, doc_id)
    
    try:
        return _execute_query(query, params)
    except mysql.connector.Error:
        return None

def get_all_documents_for_user(user_id):
    """Retrieves all documents for a specific user and decodes content."""
    query = "SELECT * FROM course_documents WHERE user_id = %s ORDER BY date_generated DESC"
    
    try:
        results = _execute_query(query, (user_id,), fetch=True) 
    except mysql.connector.Error:
        return None
        
    if results:
        return [_decode_document_fields(doc) for doc in results]
    return results


def get_document_by_title_and_user(doc_title, user_id):
    """Checks if a document with a given title exists for the user."""
    query = "SELECT doc_id, doc_title FROM course_documents WHERE doc_title = %s AND user_id = %s"
    try:
        return _execute_query(query, (doc_title, user_id), fetchone=True)
    except mysql.connector.Error:
        return None


def get_document_by_id(doc_id):
    """Retrieves a single document by its ID and decodes content."""
    query = "SELECT * FROM course_documents WHERE doc_id = %s"
    
    try:
        document = _execute_query(query, (doc_id,), fetchone=True)
    except mysql.connector.Error:
        return None
    
    return _decode_document_fields(document)


def delete_document_by_id(doc_id):
    """Deletes a document record by its ID."""
    query = "DELETE FROM course_documents WHERE doc_id = %s"
    try:
        return _execute_query(query, (doc_id,))
    except mysql.connector.Error:
        return None