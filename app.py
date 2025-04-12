import os
import requests # Library to make HTTP requests
from flask import Flask, request, render_template, url_for
import logging
import time
from dotenv import load_dotenv # Library to load .env file

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
GLIF_API_ENDPOINT = "https://simple-api.glif.app"
# --- !!! IMPORTANT: Replace with the correct Glif ID !!! ---
TARGET_GLIF_ID = "clxg3zf6p0002tgqnfwb686q0"
# --- !!! IMPORTANT: Replace with the correct internal input field name found via "View Source" !!! ---
GLIF_INPUT_NAME = "userprompt" # <-- REPLACE THIS PLACEHOLDER

# Get API Key from environment variable for security
GLIF_API_KEY = os.getenv("GLIF_API_KEY")

if not GLIF_API_KEY:
    logging.error("FATAL ERROR: GLIF_API_KEY not found in environment variables. Did you create a .env file?")
    # Optionally exit or raise an error here in a real app
    # For now, we'll let it fail later during the request

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # Disable caching for development

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def run_glif(prompt_text: str):
    """Sends a request to the Glif Simple API and returns the result."""
    if not GLIF_API_KEY:
        return {"error": "API Key not configured on server."}

    headers = {
        "Authorization": f"Bearer {GLIF_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "id": TARGET_GLIF_ID,
        "inputs": {
            # Use the correct internal input name found from Glif website
            GLIF_INPUT_NAME: prompt_text
        }
        # Use this if inputs are positional instead:
        # "inputs": [prompt_text]
    }

    logging.info(f"Sending request to Glif API for ID: {TARGET_GLIF_ID}")
    logging.info(f"Payload inputs: {payload['inputs']}") # Log input being sent

    try:
        response = requests.post(GLIF_API_ENDPOINT, headers=headers, json=payload, timeout=60) # 60 second timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        result_data = response.json()
        logging.info(f"Received response from Glif API: {result_data}")

        # Glif Simple API often returns 200 OK even for errors, check 'error' field
        if "error" in result_data:
            logging.error(f"Glif API returned an error: {result_data['error']}")
            return {"error": f"Glif API Error: {result_data['error']}"}
        elif "output" not in result_data:
             logging.error(f"Glif API response missing 'output' field: {result_data}")
             return {"error": "Glif API response missing expected output URL."}
        else:
             # Success! Return the dictionary containing the output URL
             return result_data # Contains {'output': 'http://...', ...}

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request failed: {e}", exc_info=True)
        return {"error": f"Failed to connect to Glif API: {e}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {e}"}


@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html',
                           generated_image_url=None,
                           center_message=None,
                           TARGET_GLIF_ID=TARGET_GLIF_ID)

@app.route('/generate', methods=['POST'])
def generate():
    """Handles the image generation request via Glif API."""
    original_prompt = request.form.get('prompt', '')
    portrait_mode = request.form.get('portrait_mode') == 'on'
    center_message = None

    if not original_prompt:
        center_message = "Prompt cannot be empty, retard." # Custom message for this error
        return render_template('index.html',
                               center_message=center_message, # Pass center message
                               TARGET_GLIF_ID=TARGET_GLIF_ID)
    if not GLIF_API_KEY:
         center_message = "Server Error: API Key not configured." # Keep this somewhat standard
         return render_template('index.html',
                                center_message=center_message, # Pass center message
                                TARGET_GLIF_ID=TARGET_GLIF_ID)

    # --- Modify prompt: Prepend "retarded", then handle portrait mode ---
    # Start with the core keyword
    modified_prompt = "A low IQ person, drooling from his mouth, who is... "

    # Add the user's original prompt after it
    if original_prompt: # Make sure user actually entered something
        modified_prompt += f" {original_prompt}"

    # Then prepend "portrait of " if the toggle is on
    if portrait_mode:
        modified_prompt = f"portrait of {modified_prompt}"
    # --- END Prompt Modification ---

    try:
        start_time = time.time()
        glif_result = run_glif(modified_prompt)
        end_time = time.time()
        logging.info(f"Glif API call took {end_time - start_time:.2f} seconds.")
        logging.info(f"Final Prompt Sent: '{modified_prompt}' (Original: '{original_prompt}')")

        if "error" in glif_result:
             logging.error(f"Glif API Error Detail: {glif_result['error']}")
             center_message = "i can't do that – try again, retard"
             return render_template('index.html',
                                    center_message=center_message,
                                    prompt_used=original_prompt, # Keep showing original prompt to user
                                    TARGET_GLIF_ID=TARGET_GLIF_ID)
        else:
            image_url = glif_result.get("output")
            if not image_url:
                 # --- Set generic message for center column for this specific case ---
                 center_message = "Glif response successful but missing output URL."
                 return render_template('index.html',
                                        center_message=center_message, # <-- Pass center message
                                        prompt_used=original_prompt,
                                        TARGET_GLIF_ID=TARGET_GLIF_ID)

            # Success case - no center message
            return render_template('index.html',
                                   generated_image_url=image_url,
                                   prompt_used=original_prompt,
                                   TARGET_GLIF_ID=TARGET_GLIF_ID)

    except Exception as e:
        logging.error(f"An error occurred in the generate route: {e}", exc_info=True)
        # --- Set generic internal error for center column ---
        center_message = "An internal error occurred. Oops." # Simpler message for user
        return render_template('index.html',
                               center_message=center_message, # <-- Pass center message
                               prompt_used=original_prompt,
                               TARGET_GLIF_ID=TARGET_GLIF_ID)


# --- Main Execution ---
if __name__ == '__main__':
    # Check if API key is loaded on startup
    if not GLIF_API_KEY:
         print("\n!!! WARNING: GLIF_API_KEY environment variable not set. Please create a .env file with your key. !!!\n")
    # Use host='0.0.0.0' if you want to access from other devices on your network
    # Use port 8081 or another free port
    app.run(debug=True, host='127.0.0.1', port=8082)