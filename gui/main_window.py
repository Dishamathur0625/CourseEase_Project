# gui/main_window.py (FINAL CORRECTED CODE - DUPLICATE LOGIC RESTORED & PANEL 3 FORMATTING)

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image
from datetime import datetime
import json 
import subprocess 
import re 

# External Library Dependencies 
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from docx import Document

# CRITICAL: Path for Tesseract must be correct for image reading
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from logic.llm_handler import generate_content
# --- CRITICAL CHANGE: Import database functions directly ---
from logic.db_manager import (
    get_all_documents_for_user, 
    get_document_by_title_and_user, 
    insert_document, 
    update_document, 
    delete_document_by_id,
    get_document_by_id
)
# ---

class CourseEaseApp(tk.Toplevel):

    def __init__(self, master, user_id):
        super().__init__(master)
        self.master = master
        self.user_id = user_id

        self.title(f"CourseEase - Main Application (User ID: {user_id})")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.update_idletasks()
        self.withdraw()
        self.transient(master)

        # --- CLASS VARIABLES ---
        self.doc_type_var = tk.StringVar(value="Midterm Exam") 
        self.difficulty_level_var = tk.StringVar(value="Medium")
        self.difficulty_level_options = ["Easy", "Medium", "Hard", "Very Hard"]
        self.section_type_options = ["Short Answer", "Medium Answer", "Long Answer", "Essay"]

        self.num_lectures_entry = None
        self.hours_per_lecture_var = tk.StringVar(value="1.0")
        self.hours_options = ["0.5", "1.0", "1.5", "2.0", "3.0"]

        self.num_questions_entry = None
        self.total_marks_entry = None
        self.num_sections_var = tk.StringVar(value="2")
        self.section_data_entries = []
        self.edit_mode_var = tk.BooleanVar(value=False)

        self.last_generation_params = None
        
        self.saved_documents_cache = [] 
        self.panel3_listbox = None 
        # -------------------------------------------

        self._create_main_frames()
        self._create_panel1_widgets()
        self._create_panel2_widgets()
        self._create_panel3_widgets() 

        self.deiconify()

    def _on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit CourseEase?"):
            self.destroy()
            self.master.destroy()

    def _create_main_frames(self):
        self.grid_columnconfigure(0, weight=1, uniform="panel")
        self.grid_columnconfigure(1, weight=2, uniform="panel")
        self.grid_columnconfigure(2, weight=1, uniform="panel")
        self.grid_rowconfigure(0, weight=1)
        self.panel1_frame = ttk.LabelFrame(self, text="1. Input & Configuration", padding="10")
        self.panel1_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.panel2_frame = ttk.LabelFrame(self, text="2. Output & Editor", padding="10")
        self.panel2_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.panel3_frame = ttk.LabelFrame(self, text="3. History & Controls", padding="10")
        self.panel3_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        self.panel1_frame.grid_columnconfigure(0, weight=1)

    def _create_panel1_widgets(self):
        for widget in self.panel1_frame.winfo_children(): widget.destroy()
        ttk.Label(self.panel1_frame, text="Syllabus Input", font=("Arial", 11, "bold")).pack(fill='x', pady=(0, 5))
        self.syllabus_text = scrolledtext.ScrolledText(self.panel1_frame, wrap=tk.WORD, height=10, font=("Arial", 10))
        self.syllabus_text.insert(tk.END, "Paste Syllabus Here...")
        self.syllabus_text.pack(fill='both', expand=True, padx=5, pady=5)
        ttk.Button(self.panel1_frame, text="Upload Syllabus File", command=self._upload_syllabus).pack(fill='x', pady=(0, 10), padx=5)
        ttk.Label(self.panel1_frame, text="Select Document Type", font=("Arial", 11, "bold")).pack(fill='x', pady=(10, 5))
        radio_frame = ttk.Frame(self.panel1_frame)
        radio_frame.pack(fill='x', padx=5)
        doc_types = ["Single Lecture", "Lecture Plan", "Assignments", "Midterm Exam", "Final Exam"]
        col_count = 0
        for text in doc_types:
            rb = ttk.Radiobutton(radio_frame, text=text, variable=self.doc_type_var, value=text, command=self._on_doc_type_change)
            rb.grid(row=col_count // 2, column=col_count % 2, sticky="w", padx=5, pady=2)
            col_count += 1
        ttk.Label(self.panel1_frame, text="Generation Parameters", font=("Arial", 11, "bold")).pack(fill='x', pady=(10, 5))
        self.param_container = ttk.Frame(self.panel1_frame)
        self.param_container.pack(fill='x', padx=5, pady=5)
        self._on_doc_type_change()
        
        # --- BUTTON CALLING THE MISSING METHOD ---
        ttk.Button(self.panel1_frame, text="GENERATE DOCUMENT", command=self._generate_document_from_panel1).pack(fill='x', pady=20, padx=5)

    def _on_doc_type_change(self):
        """Dynamically updates the Generation Parameters section based on radio button selection."""
        for widget in self.param_container.winfo_children(): widget.destroy()
        selected_type = self.doc_type_var.get()
        self.param_container.grid_columnconfigure(1, weight=1)
        row_count = 0
        self.num_lectures_entry = None; self.num_questions_entry = None; self.total_marks_entry = None; self.section_data_entries = []

        if selected_type == "Single Lecture":
            ttk.Label(self.param_container, text="(No specific parameters needed for single lecture content)").grid(row=0, column=0, columnspan=2, pady=5)
        elif selected_type == "Lecture Plan":
            ttk.Label(self.param_container, text="Total Lectures:").grid(row=row_count, column=0, sticky="w", pady=2, padx=2)
            self.num_lectures_entry = ttk.Entry(self.param_container); self.num_lectures_entry.insert(0, "14"); self.num_lectures_entry.grid(row=row_count, column=1, sticky="ew", padx=5); row_count += 1
            ttk.Label(self.param_container, text="Hours/Lecture:").grid(row=row_count, column=0, sticky="w", pady=2, padx=2)
            self.hours_per_lecture_var.set("1.0"); ttk.Combobox(self.param_container, textvariable=self.hours_per_lecture_var, values=self.hours_options, state="readonly").grid(row=row_count, column=1, sticky="ew", padx=5); row_count += 1
        elif selected_type == "Assignments":
            ttk.Label(self.param_container, text="Num Questions:").grid(row=row_count, column=0, sticky="w", pady=2, padx=2)
            self.num_questions_entry = ttk.Entry(self.param_container); self.num_questions_entry.insert(0, "10"); self.num_questions_entry.grid(row=row_count, column=1, sticky="ew", padx=5); row_count += 1
        elif selected_type in ["Midterm Exam", "Final Exam"]:
            ttk.Label(self.param_container, text="Overall Difficulty:").grid(row=row_count, column=0, sticky="w", pady=5, padx=2)
            self.difficulty_level_var.set("Medium"); ttk.Combobox(self.param_container, textvariable=self.difficulty_level_var, values=self.difficulty_level_options, state="readonly").grid(row=row_count, column=1, sticky="ew", padx=5); row_count += 1
            ttk.Label(self.param_container, text="Number of Sections:").grid(row=row_count, column=0, sticky="w", pady=5, padx=2)
            section_options = ["1", "2", "3", "4"]; self.num_sections_var.set("2")
            section_combo = ttk.Combobox(self.param_container, textvariable=self.num_sections_var, values=section_options, state="readonly"); section_combo.grid(row=row_count, column=1, sticky="ew", padx=5); row_count += 1
            section_combo.bind("<<ComboboxSelected>>", self._build_exam_sections)
            self.section_detail_container = ttk.Frame(self.param_container); self.section_detail_container.grid(row=row_count, column=0, columnspan=2, sticky="ew", pady=(10, 0))
            self._build_exam_sections(event=None)

    def _build_exam_sections(self, event=None):
        """Dynamically creates the Type, Qty, and Marks Per Question inputs for each section."""
        for widget in self.section_detail_container.winfo_children(): widget.destroy()
        self.section_data_entries.clear() 
        try: num_sections = int(self.num_sections_var.get())
        except ValueError: num_sections = 1
        header_frame = ttk.Frame(self.section_detail_container); header_frame.pack(fill='x', pady=(0, 5))
        header_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="section_col")
        ttk.Label(header_frame, text="Section", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", padx=2)
        ttk.Label(header_frame, text="Type", font=("Arial", 9, "bold")).grid(row=0, column=1, sticky="ew")
        ttk.Label(header_frame, text="Qty", font=("Arial", 9, "bold")).grid(row=0, column=2, sticky="ew")
        ttk.Label(header_frame, text="Marks/Q", font=("Arial", 9, "bold")).grid(row=0, column=3, sticky="ew")
        ttk.Label(header_frame, text="Total", font=("Arial", 9, "bold")).grid(row=0, column=4, sticky="ew")
        for i in range(num_sections):
            section_frame = ttk.Frame(self.section_detail_container); section_frame.pack(fill='x', pady=1, padx=5)
            section_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="section_col")
            section_name = f"Section {chr(65+i)}"
            ttk.Label(section_frame, text=f"{section_name}:").grid(row=0, column=0, sticky="w", padx=2)
            type_var = tk.StringVar(value=self.section_type_options[i % len(self.section_type_options)])
            type_combo = ttk.Combobox(section_frame, textvariable=type_var, values=self.section_type_options, state="readonly", width=8); type_combo.grid(row=0, column=1, sticky="ew", padx=2)
            questions_entry = ttk.Entry(section_frame, width=5); questions_entry.insert(0, "5"); questions_entry.grid(row=0, column=2, sticky="ew", padx=2)
            mpq_entry = ttk.Entry(section_frame, width=5); mpq_entry.insert(0, "2"); mpq_entry.grid(row=0, column=3, sticky="ew", padx=2)
            total_label = ttk.Label(section_frame, text="10", background="#E0E0E0"); total_label.grid(row=0, column=4, sticky="ew", padx=2)
            self.section_data_entries.append({
                "section_name": section_name, "type_var": type_var, "questions_entry": questions_entry,
                "mpq_entry": mpq_entry, "total_label": total_label
            })

    def _create_panel2_widgets(self):
        """Builds the widgets for the Output & Editor panel."""
        control_frame = ttk.Frame(self.panel2_frame); control_frame.pack(fill='x', pady=5, padx=5)
        ttk.Label(control_frame, text="Title:").pack(side=tk.LEFT, padx=5)
        self.doc_title_entry = ttk.Entry(control_frame, font=("Arial", 10, "bold")); self.doc_title_entry.insert(0, "New Document - Unsaved"); self.doc_title_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        ttk.Label(control_frame, text="Allow Edits:").pack(side=tk.LEFT, padx=(15, 5))
        ttk.Checkbutton(control_frame, variable=self.edit_mode_var, text="", command=self._toggle_editor_state).pack(side=tk.LEFT)
        self.regenerate_button = ttk.Button(control_frame, text="🔄 Regenerate", command=self._regenerate_document, state=tk.DISABLED); self.regenerate_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="💾 Save", command=self._save_document).pack(side=tk.RIGHT, padx=5)
        self.editor_text = scrolledtext.ScrolledText(self.panel2_frame, wrap=tk.WORD, font=("Consolas", 11), padx=10, pady=10, bg="#f5f5f5", state=tk.DISABLED)
        self.editor_text.insert(tk.END, "Generated content will appear here after clicking 'GENERATE DOCUMENT' in Panel 1.\n\n")
        self.editor_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.status_label = ttk.Label(self.panel2_frame, text="Status: Waiting for request from Panel 1.", anchor="w", relief="sunken"); self.status_label.pack(fill='x', padx=5, pady=(0, 5))

    def _create_panel3_widgets(self):
        """Builds the widgets for the History & Controls panel."""
        self.panel3_frame.grid_columnconfigure(0, weight=1); self.panel3_frame.grid_rowconfigure(0, weight=1)
        
        # --- CRITICAL FIX 1: Change show="headings" to show="tree headings" ---
        # This makes column #0 (where the Title/text goes) visible.
        self.panel3_listbox = ttk.Treeview(self.panel3_frame, columns=("Format", "Date"), show="tree headings", selectmode='browse')
        
        # --- START CHANGE 2: Update Headers ---
        # #0 Column displays the 'text' property, which is the document title.
        self.panel3_listbox.heading("#0", text="Document Name", anchor=tk.W)
        self.panel3_listbox.heading("Format", text="Saved As", anchor=tk.CENTER)
        self.panel3_listbox.heading("Date", text="Created On", anchor=tk.CENTER)
        # --- END CHANGE 2 ---
        
        # Adjust column widths to better show Title and Format
        self.panel3_listbox.column("#0", stretch=tk.YES, width=150)
        self.panel3_listbox.column("Format", stretch=tk.NO, width=70, anchor=tk.CENTER) 
        self.panel3_listbox.column("Date", stretch=tk.NO, width=80, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(self.panel3_frame, orient=tk.VERTICAL, command=self.panel3_listbox.yview)
        self.panel3_listbox.configure(yscrollcommand=scrollbar.set)
        self.panel3_listbox.grid(row=0, column=0, columnspan=3, sticky='nsew', padx=5, pady=5); scrollbar.grid(row=0, column=3, sticky='ns')
        self.panel3_listbox.bind("<Double-1>", self._on_listbox_double_click) 
        control_frame = ttk.Frame(self.panel3_frame); control_frame.grid(row=1, column=0, columnspan=4, sticky='ew', padx=5, pady=(5,0))
        control_frame.grid_columnconfigure((0, 1), weight=1)
        ttk.Button(control_frame, text="🗑️ Delete File", command=self._delete_saved_file).grid(row=0, column=0, sticky='ew', padx=2, pady=5)
        ttk.Button(control_frame, text="💾 Save to Device", command=self._save_file_to_device_selected).grid(row=0, column=1, sticky='ew', padx=2, pady=5)
        self._refresh_panel3_listbox() 

    # --- CORE GENERATION LOGIC (Omitted for brevity) ---

    def _start_generation_process(self, use_last_params=False):
        """Gathers inputs and initiates the document generation in a separate thread."""
        syllabus_content = self.syllabus_text.get(1.0, tk.END).strip()
        if not syllabus_content or syllabus_content == "Paste Syllabus Here...":
            messagebox.showwarning("Input Error", "Please paste or upload syllabus content.")
            return

        doc_type = self.doc_type_var.get(); parameters = {}
        
        if use_last_params and self.last_generation_params:
            doc_type = self.last_generation_params["doc_type"]
            parameters = self.last_generation_params["params"]
            self.last_generation_params["syllabus"] = syllabus_content 
        else:
            if doc_type == "Single Lecture": pass
            elif doc_type == "Lecture Plan":
                if self.num_lectures_entry:
                    parameters["total_lectures"] = self.num_lectures_entry.get()
                    parameters["hours_per_lecture"] = self.hours_per_lecture_var.get()
                else: messagebox.showwarning("Input Error", "Lecture Plan parameters are missing."); return
            elif doc_type == "Assignments":
                if self.num_questions_entry:
                    parameters["num_questions"] = self.num_questions_entry.get()
                else: messagebox.showwarning("Input Error", "Assignments requires 'Num Questions' parameter."); return
            elif doc_type in ["Midterm Exam", "Final Exam"]:
                if not self.section_data_entries: messagebox.showwarning("Input Error", "Exam structure is missing. Please configure sections."); return
                exam_sections = []; total_exam_marks_sum = 0; total_question_sum = 0
                for section in self.section_data_entries:
                    try: q_count = int(section["questions_entry"].get()); mpq = int(section["mpq_entry"].get())
                    except ValueError: messagebox.showerror("Input Error", "Question Count and Marks must be valid integers."); return
                    if q_count <= 0 or mpq <= 0: messagebox.showerror("Input Error", "Question Count and Marks must be greater than zero."); return
                    section_total_marks = q_count * mpq; total_exam_marks_sum += section_total_marks; total_question_sum += q_count
                    section["total_label"].config(text=str(section_total_marks))
                    exam_sections.append({ "section_name": section["section_name"], "section_type": section["type_var"].get(), "question_count": q_count, "marks_per_question": mpq, "total_section_marks": section_total_marks})
                parameters = {
                    "overall_total_marks": total_exam_marks_sum, "overall_total_questions": total_question_sum,
                    "overall_difficulty_suggestion": self.difficulty_level_var.get(), "sections_details": exam_sections }
            
            self.last_generation_params = { "syllabus": syllabus_content, "doc_type": doc_type, "params": parameters }
            
        self.regenerate_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Generating content... Please wait. (Running in background)"); self.update_idletasks()
        thread = threading.Thread(target=self._thread_generate, args=(self.last_generation_params,), daemon=True); thread.start()

    # --- MISSING METHOD ADDED (Omitted for brevity) ---
    def _generate_document_from_panel1(self):
        """Public method called by Panel 1's GENERATE DOCUMENT button. FIXES AttributeError."""
        self._start_generation_process(use_last_params=False)

    def _regenerate_document(self):
        """Public method called by Panel 2's REGENERATE button."""
        if self.last_generation_params: self._start_generation_process(use_last_params=True)
        else: messagebox.showwarning("Regeneration Error", "No previous generation parameters found. Please generate a document first from Panel 1."); self.regenerate_button.config(state=tk.DISABLED)

    def _thread_generate(self, generation_data):
        """Worker function executed in a separate thread to call the LLM API."""
        generated_text, success = generate_content(
            generation_data['syllabus'], generation_data['doc_type'], generation_data['params']
        )
        if success:
            difficulty = generation_data['params'].get('overall_difficulty_suggestion', 'General')
            self.master.after(0, lambda: self._update_panel2_success(
                generated_text, generation_data['doc_type'], difficulty
            ))
        else:
            self.master.after(0, lambda: self._update_panel2_failure(generated_text))

    def _update_panel2_success(self, generated_text, doc_type, difficulty):
        """Safely updates Panel 2 widgets on the main thread upon successful generation."""
        self.editor_text.config(state=tk.NORMAL); self.editor_text.delete(1.0, tk.END)
        self.editor_text.insert(tk.END, generated_text)
        if not self.edit_mode_var.get(): self.editor_text.config(state=tk.DISABLED); title_status = "Editor Locked"
        else: title_status = "Editing Enabled"
        self.editor_text.config(state=tk.DISABLED)
        title_difficulty = difficulty.title() if difficulty != 'General' else ''
        self.doc_title_entry.delete(0, tk.END); self.doc_title_entry.insert(0, f"{doc_type} - {title_difficulty} Draft")
        self.status_label.config(text="Status: Generation complete. Ready for review.")
        messagebox.showinfo("Success", "Content generated! Review in Panel 2."); self.regenerate_button.config(state=tk.NORMAL) 

    def _update_panel2_failure(self, error_message):
        """Safely updates Panel 2 widgets on the main thread upon generation failure."""
        self.editor_text.config(state=tk.NORMAL); self.status_label.config(text="Status: ERROR! Check API Key/Connection.")
        self.editor_text.delete(1.0, tk.END); self.editor_text.insert(tk.END, f"GENERATION FAILED.\n\nError Details:\n{error_message}")
        messagebox.showerror("Generation Failed", error_message); self.editor_text.config(state=tk.DISABLED)
        self.regenerate_button.config(state=tk.NORMAL)

    def _toggle_editor_state(self):
        """Switches the state of the editor between NORMAL (editable) and DISABLED (locked)."""
        if self.edit_mode_var.get():
            self.editor_text.config(state=tk.NORMAL); self.status_label.config(text="Status: Editing Enabled. Content can be manually modified.")
        else:
            self.editor_text.config(state=tk.DISABLED); self.status_label.config(text="Status: Editor Locked. Content integrity preserved.")

    # --- FILE/SYLLABUS LOGIC (Omitted for brevity) ---
    def _upload_syllabus(self):
        """Handles file upload and text extraction."""
        filepath = filedialog.askopenfilename(filetypes=[("All Supported Docs", "*.txt *.pdf *.jpg *.jpeg *.png")])
        if not filepath: return
        filename = os.path.basename(filepath); self.syllabus_text.delete(1.0, tk.END); extracted_text = ""; file_ext = filename.lower().split('.')[-1]
        try:
            if file_ext == 'txt': 
                with open(filepath, 'r', encoding='utf-8') as f: extracted_text = f.read()
            elif file_ext == 'pdf': reader = PdfReader(filepath); text_pages = [page.extract_text() for page in reader.pages]; extracted_text = "\n".join(text_pages)
            elif file_ext in ('jpg', 'jpeg', 'png'): extracted_text = pytesseract.image_to_string(Image.open(filepath))
            else: self.syllabus_text.insert(tk.END, f"File type (. {file_ext}) is unsupported."); messagebox.showwarning("Unsupported Type", f"File type (. {file_ext}) is not supported."); return
            if extracted_text.strip(): self.syllabus_text.insert(tk.END, extracted_text); messagebox.showinfo("Upload Success", f"Content from {filename} loaded successfully.")
            else: self.syllabus_text.insert(tk.END, f"Warning: Content from {filename} was empty."); messagebox.showwarning("Extraction Warning", f"Could not extract meaningful text from {filename}.")
        except Exception as e:
            error_msg = f"Error reading {filename}: {type(e).__name__}."; self.syllabus_text.insert(tk.END, f"--- EXTRACTION FAILED ---\n{error_msg}"); messagebox.showerror("Reading Error", error_msg)

    # --- PANEL 3 INTERACTION LOGIC (DB Integrated) ---

    def _get_selected_doc_id(self):
        """Helper to get the doc_id of the currently selected item."""
        selected_item_id = self.panel3_listbox.focus()
        if not selected_item_id: return None
        return int(selected_item_id) 

    def _get_doc_from_cache(self, doc_id):
        """Retrieves a document from the local cache."""
        return next((doc for doc in self.saved_documents_cache if doc.get('doc_id') == doc_id), None)

    def _refresh_panel3_listbox(self):
        """Fetches data from the DB, updates cache, and repopulates the listbox."""
        if not self.panel3_listbox: return

        for item in self.panel3_listbox.get_children(): self.panel3_listbox.delete(item)

        try:
            self.saved_documents_cache = get_all_documents_for_user(self.user_id) 
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve documents from history. Ensure DB is connected: {e}")
            self.saved_documents_cache = []

        if self.saved_documents_cache is None: self.saved_documents_cache = []
            
        for doc in self.saved_documents_cache:
            doc_id = doc.get('doc_id')
            # doc_type is no longer used as a column but is available in doc.get('doc_type')
            date_generated = doc.get('date_generated')
            
            # --- START CHANGE 3: Extract Saved Format ---
            saved_format = "N/A" # Default if parameters are missing
            try:
                gen_params = json.loads(doc.get('generation_params', '{}'))
                saved_format = gen_params.get('saved_as_format', 'N/A')
            except (json.JSONDecodeError, TypeError):
                pass # Keep default N/A
            # --- END CHANGE 3 ---
            
            # Repopulate listbox.
            # The document title goes into the 'text' property (Column #0/Document Name)
            self.panel3_listbox.insert(
                "", tk.END, iid=doc_id, text=doc.get('doc_title', 'Untitled Document'), 
                values=(saved_format, str(date_generated).split(' ')[0]) # values go into columns 'Format' and 'Date'
            )

    def _on_listbox_double_click(self, event):
        """
        Handles double-click event on a saved file entry. 
        ACTION: Opens the file immediately using the stored format.
        """
        doc_id = self._get_selected_doc_id()
        if doc_id:
            # CRITICAL CHANGE: Call the new open function instead of the save function
            self._open_file_in_app(doc_id)
        else:
            messagebox.showwarning("Selection Error", "Please select a file to open.")

    def _get_document_data_for_action(self, doc_id):
        """Helper to retrieve all necessary document data by ID."""
        selected_doc = self._get_doc_from_cache(doc_id)
        if not selected_doc:
            # If not in cache, try fetching from DB
            selected_doc = get_document_by_id(doc_id)
        
        if not selected_doc:
            messagebox.showerror("Error", "Could not find selected document in history.")
            return None, None, None

        content = selected_doc.get('content')
        if not content:
            messagebox.showerror("Error", "Selected document content is empty.")
            return None, None, None
            
        try:
            gen_params = json.loads(selected_doc.get('generation_params', '{}'))
            # Retrieve the saved format (e.g., 'PDF' or 'Word')
            save_format = gen_params.get('saved_as_format', 'PDF') 
        except:
            save_format = 'PDF'
            
        title = selected_doc.get('doc_title', 'Document')
        
        return content, save_format, title


    def _open_file_in_app(self, doc_id):
        """
        Generates the document file in a temporary location and opens it 
        using the default system viewer.
        """
        content, save_format, title = self._get_document_data_for_action(doc_id)
        if content is None:
            return

        # 1. Determine temporary file path and extension
        file_ext = ".pdf" if save_format == 'PDF' else ".docx"
        
        # Use a temporary file name to avoid polluting the user's main directory
        temp_dir = os.path.join(os.path.expanduser('~'), 'CourseEase_Temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique temp filename based on the document ID and format
        temp_filepath = os.path.join(temp_dir, f"{title.replace(' ', '_')}_{doc_id}_temp{file_ext}")
        
        try:
            # 2. Create the temporary file
            if save_format == 'PDF':
                self._create_pdf(temp_filepath, content)
            elif save_format == 'Word':
                self._create_word(temp_filepath, content)
            
            # 3. Open the file using the default system program
            if os.name == 'nt':  # Windows
                os.startfile(temp_filepath)
            elif os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', temp_filepath))
            else:  # Linux/Other (requires 'xdg-open')
                subprocess.call(('xdg-open', temp_filepath))
                
            messagebox.showinfo("Opening File", f"Opening '{title}' in your default viewer as a {save_format} file.")

        except FileNotFoundError:
            messagebox.showerror("Open Error", "Error: The necessary system command ('open' or 'xdg-open') was not found to open the file. Try manually opening from the temp folder.")
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to open the file: {e}")
            

    def _save_file_to_device_selected(self, doc_id=None):
        """
        Exports the selected file from Panel 3 to the user's device (User clicks the button).
        (Function remains responsible for the 'Save to Device' button.)
        """
        if doc_id is None:
            doc_id = self._get_selected_doc_id()
            if doc_id is None: messagebox.showwarning("Selection Error", "Please select a file in Panel 3 to save to device."); return

        content, save_format, title = self._get_document_data_for_action(doc_id)
        if content is None:
            return

        # 1. Ask for file format (User initiated save)
        save_format = self._ask_for_save_format(
            "Save File to Device",
            f"Choose format to export '{title}':"
        )
        if not save_format: return

        # 2. Get save location and save the file
        default_filename = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
        file_ext = ".pdf" if save_format == 'PDF' else ".docx"

        filepath = filedialog.asksaveasfilename(
            defaultextension=file_ext, initialfile=default_filename, 
            filetypes=[(f"{save_format} Document", f"*{file_ext}"), ("All Files", "*.*")]
        )
        if not filepath: return

        try:
            if save_format == 'PDF': self._create_pdf(filepath, content)
            elif save_format == 'Word': self._create_word(filepath, content)
            messagebox.showinfo("Save Success", f"File exported successfully to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Save Error", f"An error occurred while saving the file: {e}")

    def _delete_saved_file(self):
        """Deletes the selected file from Panel 3 and the database."""
        doc_id = self._get_selected_doc_id();
        if doc_id is None: messagebox.showwarning("Selection Error", "Please select a file to delete."); return
        selected_title = self.panel3_listbox.item(self.panel3_listbox.focus(), 'text')

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the file: '{selected_title}'? This will be permanently removed from the database."):
            try:
                if delete_document_by_id(doc_id): 
                    self._refresh_panel3_listbox()
                    messagebox.showinfo("Delete Success", "File deleted successfully from history and database.")
                else:
                    messagebox.showerror("Delete Error", "File could not be found or deleted in the database.")
            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred during deletion: {e}")

    # --- CUSTOM DIALOG FOR DUPLICATE HANDLING ---
    def _ask_for_duplicate_action(self, title):
        """Creates a custom dialog for duplicate file resolution."""
        dialog = tk.Toplevel(self)
        dialog.title("File Conflict")
        
        main_x = self.winfo_x() + self.winfo_width() // 2 - 200
        main_y = self.winfo_y() + self.winfo_height() // 2 - 100
        dialog.geometry(f"400x150+{main_x}+{main_y}")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text=f"The document '{title}' already exists.", font=("Arial", 11, "bold"), padding=5).pack(pady=(10, 5))
        ttk.Label(dialog, text="Do you want to replace it, or save a new copy?", padding=5).pack(pady=(0, 10))

        self.duplicate_choice = None
        def set_choice_and_close(action):
            self.duplicate_choice = action
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="🔁 Replace Existing", command=lambda: set_choice_and_close('replace')).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="➕ Create New (Copy)", command=lambda: set_choice_and_close('copy')).pack(side=tk.LEFT, padx=10)
        
        self.wait_window(dialog)
        return self.duplicate_choice
        
    # --- CORE SAVE LOGIC ---
    def _ask_for_save_format(self, title, prompt):
        """Creates a dialog to ask the user for the save format (PDF or Word)."""
        dialog = tk.Toplevel(self); dialog.title(title)
        main_x = self.winfo_x() + self.winfo_width() // 2 - 150; main_y = self.winfo_y() + self.winfo_height() // 2 - 75
        dialog.geometry(f"300x150+{main_x}+{main_y}"); dialog.transient(self); dialog.grab_set()

        ttk.Label(dialog, text=prompt, padding=10, wraplength=280).pack(pady=10)
        self.save_format_choice = None 
        def set_choice_and_close(format_type): self.save_format_choice = format_type; dialog.destroy()
        button_frame = ttk.Frame(dialog); button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Save as PDF", command=lambda: set_choice_and_close('PDF')).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Save as Word (.docx)", command=lambda: set_choice_and_close('Word')).pack(side=tk.LEFT, padx=10)
        self.wait_window(dialog); return self.save_format_choice

    def _get_unique_copy_title(self, base_title):
        """
        Generates a unique title like 'Base Name Copy(1)' 
        """
        copy_count = 1
        
        # Strip existing copy notation to get the true base name
        base_name = re.sub(r' Copy\(\d+\)$', '', base_title).strip()
        
        new_title = f"{base_name} Copy({copy_count})"
        
        # Check against the cache (quick check) and then the DB
        while any(doc['doc_title'] == new_title for doc in self.saved_documents_cache) or get_document_by_title_and_user(new_title, self.user_id):
            copy_count += 1
            new_title = f"{base_name} Copy({copy_count})"
        return new_title

    def _save_document(self):
        """Handles confirmation, duplicate check, format selection, and database save."""
        document_content = self.editor_text.get(1.0, tk.END).strip(); 
        document_title = self.doc_title_entry.get().strip()
        doc_type = self.doc_type_var.get(); 
        syllabus_used = self.syllabus_text.get(1.0, tk.END).strip()
        
        if not document_content or "Generated content will appear here" in document_content: 
            messagebox.showwarning("Save Error", "No generated content available to save."); 
            return
            
        # 0. Handle Untitled Drafts
        is_untitled = False
        if not document_title or document_title == "New Document - Unsaved":
            document_title = f"{doc_type} - Draft - {datetime.now().strftime('%Y-%m-%d %H%M%S')}"
            is_untitled = True
            
        final_title_to_save = document_title
        existing_doc = get_document_by_title_and_user(final_title_to_save, self.user_id) 

        # 1. Duplicate Check & Resolution
        if existing_doc and not is_untitled:
            action = self._ask_for_duplicate_action(document_title) # RESTORED: Custom dialog
            if action == 'replace':
                pass # Proceed to update (overwrite)
            elif action == 'copy':
                # Generate unique name in the correct format
                final_title_to_save = self._get_unique_copy_title(document_title)
                existing_doc = None # Treat as a new insert
            else:
                messagebox.showinfo("Save Cancelled", "Saving to history was cancelled."); 
                return
            
        # 2. Ask for Save Format
        save_format = self._ask_for_save_format("Save Format Selection", "On what type of document do you want to save this?")
        if not save_format: messagebox.showinfo("Save Cancelled", "Saving to history was cancelled."); return

        # 3. Prepare Data for DB (including save format in JSON field)
        generation_params_dict = self.last_generation_params['params'] if self.last_generation_params else {}
        generation_params_dict['saved_as_format'] = save_format
        generation_params_json = json.dumps(generation_params_dict)
        
        doc_data = (final_title_to_save, doc_type, syllabus_used, document_content, generation_params_json) # Using final_title_to_save

        # 4. Save/Update to Database
        try:
            # Perform DB operation
            if existing_doc:
                success = update_document(existing_doc['doc_id'], *doc_data); action = "replaced"
            else:
                success = insert_document(self.user_id, *doc_data); action = "saved"
            
            if success:
                # Panel 3 Synchronization: This pulls the new/updated title (including Copy(N)) from DB
                self._refresh_panel3_listbox() 
                
                messagebox.showinfo("Save Success", f"'{final_title_to_save}' successfully {action} to the database and is visible in Panel 3.")
                
                # Panel 2 Synchronization: Ensure the editor title reflects the saved name, 
                # or is reset if logic dictates (here, we keep the saved name)
                self.doc_title_entry.delete(0, tk.END)
                self.doc_title_entry.insert(0, final_title_to_save)
                
            else: messagebox.showerror("Database Error", "Failed to save/update document in the database.")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred during database save: {e}. Check console for details.")

    # --- FILE CREATION HELPERS (Omitted for brevity) ---
    def _create_pdf(self, filepath, content):
        c = canvas.Canvas(filepath, pagesize=letter); c.setFont("Helvetica", 10)
        width, height = letter; x = 36; y = height - 36
        for line in content.split('\n'):
            if y < 50: c.showPage(); c.setFont("Helvetica", 10); y = height - 36
            c.drawString(x, y, line); y -= 12
        c.save()

    def _create_word(self, filepath, content):
        document = Document()
        for line in content.split('\n'): document.add_paragraph(line)
        document.save(filepath)