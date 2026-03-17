# app.py

import tkinter as tk
from gui.login_signup_window import LoginSignupWindow
from gui.main_window import CourseEaseApp 

class App:
    def __init__(self, root):
        self.root = root
        self.root.withdraw() 
        self.current_session_user_id = None
        
        # Start the application by displaying the Login window
        self.login_signup_window = LoginSignupWindow(root, self._on_login_success)

    def _on_login_success(self, user_id):
        """Callback function executed after successful login."""
        self.current_session_user_id = user_id
        
        # Launch the main application, passing the user_id for session management
        self.main_app = CourseEaseApp(self.root, user_id=self.current_session_user_id)
        # The main_app's __init__ now handles its own display
        

if __name__ == "__main__":
    # Create the root window but keep it hidden as a container
    root = tk.Tk()
    root.withdraw() 
    app = App(root)
    root.mainloop()