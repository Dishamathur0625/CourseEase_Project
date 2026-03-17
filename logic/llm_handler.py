
from google import genai
from google.genai import types
from config.settings import GEMINI_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- INITIALIZE THE GEMINI CLIENT OBJECT ---
client = None
try:
    # Initialize the client using the API key from settings.py
    client = genai.Client(api_key=GEMINI_API_KEY)
    logging.info("Gemini API client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Gemini client: {e}")

# Use a powerful model for structured generation
MODEL_NAME = "gemini-2.5-flash" 

def generate_content(syllabus_text, doc_type, parameters):
    """
    Sends the request to the Gemini API to generate content.
    (This function is called by the 'GENERATE DOCUMENT' button.)
    """
    if client is None:
        return "Error: Gemini API client failed to initialize. Check API key in settings.py.", False

    # --- System Instruction (Defines the AI's role) ---
    system_instruction = (
        "You are 'CourseEase AI', an expert academic assistant specializing in generating structured course materials. "
        "Your response must be ONLY the generated document content. Use Markdown for all formatting, including headings, "
        "bold text, and lists. Do not include any introductory or concluding remarks outside the document itself."
    )
    
    # --- User Prompt (The content request) ---
    user_prompt = (
        f"Generate a '{doc_type}' document. The parameters are: {parameters}. "
        f"The official syllabus content is provided below:\n\n---\n{syllabus_text}"
    )
    
    # Combine system and user instructions
    messages = [
         types.Content(role="user", parts=[types.Part(text=user_prompt)]) 
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.5,
        max_output_tokens=6000
    )

    try:
        # 1. Call the Gemini API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=messages,
            config=config
        )
        
        # 2. Extract and return the generated text
        if response.text:
            generated_text = response.text
            return generated_text, True
        else:
            return f"Gemini returned an empty response. Reason: {response.candidates[0].finish_reason}", False

    except genai.errors.APIError as e:
        logging.error(f"Gemini API Error during generation: {e}")
        return f"API Error: Could not generate content. {e}", False
    except Exception as e:
        logging.error(f"An unexpected error occurred in LLM handler: {e}")
        return f"Unexpected Error: {e}", False