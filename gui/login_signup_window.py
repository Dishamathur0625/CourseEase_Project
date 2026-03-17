# gui/login_signup_window.py

import tkinter as tk
from tkinter import messagebox
# Import the authentication logic functions from your backend module
from logic.db_manager import register_user, authenticate_user 

class LoginSignupWindow(tk.Toplevel):
    def __init__(self, master, on_login_success_callback):
        super().__init__(master)
        self.master = master
        self.on_login_success_callback = on_login_success_callback
        self.title("CourseEase - Login/Signup")
        self.geometry("400x400")
        self.resizable(False, False)
        self.grab_set() 

        # Centering logic
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self._current_user_id = None # Store ID after successful login

        self._create_widgets()
        self.show_login_frame()

    def _create_widgets(self):
        self.login_frame = tk.Frame(self)
        self.signup_frame = tk.Frame(self)

        # --- Login Frame Setup (Widgets, Labels, Entries) ---
        tk.Label(self.login_frame, text="CourseEase", font=("Arial", 24, "bold"), fg="#1E90FF").pack(pady=20)
        
        tk.Label(self.login_frame, text="Username:").pack(pady=(10, 0))
        self.login_username_entry = tk.Entry(self.login_frame, width=30)
        self.login_username_entry.pack()

        tk.Label(self.login_frame, text="Password:").pack(pady=(10, 0))
        self.login_password_entry = tk.Entry(self.login_frame, show="*", width=30)
        self.login_password_entry.pack()

        # Wire Login Button to backend function
        tk.Button(self.login_frame, text="Login", command=self._handle_login, bg="#1E90FF", fg="white", font=("Arial", 12, "bold")).pack(pady=20, ipadx=20)

        tk.Button(self.login_frame, text="Don't have an account? Sign Up", command=self.show_signup_frame, relief="flat", fg="#1E90FF").pack()

        # --- Signup Frame Setup ---
        tk.Label(self.signup_frame, text="CourseEase", font=("Arial", 24, "bold"), fg="#1E90FF").pack(pady=20)
        
        tk.Label(self.signup_frame, text="Username:").pack(pady=(10, 0))
        self.signup_username_entry = tk.Entry(self.signup_frame, width=30)
        self.signup_username_entry.pack()

        tk.Label(self.signup_frame, text="Password:").pack(pady=(10, 0))
        self.signup_password_entry = tk.Entry(self.signup_frame, show="*", width=30)
        self.signup_password_entry.pack()

        # Wire Sign Up Button to backend function
        tk.Button(self.signup_frame, text="Sign Up", command=self._handle_signup, bg="#1E90FF", fg="white", font=("Arial", 12, "bold")).pack(pady=20, ipadx=20)

        tk.Button(self.signup_frame, text="Already have an account? Login", command=self.show_login_frame, relief="flat", fg="#1E90FF").pack()

    # --- Frame Switching Logic ---
    def show_login_frame(self):
        self.signup_frame.pack_forget()
        self.login_frame.pack(expand=True, fill="both")

    def show_signup_frame(self):
        self.login_frame.pack_forget()
        self.signup_frame.pack(expand=True, fill="both")

    # --- Authentication Handlers (Connects to logic/db_manager.py) ---
    def _handle_login(self):
        username = self.login_username_entry.get()
        password = self.login_password_entry.get()

        if not username or not password:
            messagebox.showerror("Login Error", "Please enter both username and password.")
            return

        # CALL BACKEND LOGIC
        success, message, user_id = authenticate_user(username, password) 
        
        if success:
            self._current_user_id = user_id
            messagebox.showinfo("Login Success", message)
            self.destroy() 
            # Call the main app launcher function
            self.on_login_success_callback(user_id=self._current_user_id) 
        else:
            messagebox.showerror("Login Failed", message)

    def _handle_signup(self):
        username = self.signup_username_entry.get()
        password = self.signup_password_entry.get()

        if not username or not password:
            messagebox.showerror("Signup Error", "Please fill in all required fields.")
            return
        
        # CALL BACKEND LOGIC
        success, message = register_user(username, password)
        
        if success:
            messagebox.showinfo("Signup Success", message)
            self.show_login_frame() # Switch to login after success
        else:
            messagebox.showerror("Signup Failed", message)


# Assuming main_window.py has the CourseEaseApp class structure.
# We will now update app.py to use this LoginSignupWindow.