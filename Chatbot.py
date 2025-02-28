# Import necessary libraries
import streamlit as st  # Web application framework for creating interactive UIs
from dotenv import load_dotenv  # Library to load environment variables from .env file
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage  # Message types from LangChain
import weave  # Analytics and monitoring tool
from typing import Optional, Tuple  # Type hints for better code readability
import threading  # For running background tasks
import time  # For time-related operations
import os  # For operating system dependent functionality

# Import custom modules
from MultiAgent import MultiAgents  # Custom module for handling multiple AI agents
from utils import download_and_extract_zip_from_drive  # Helper function to download files

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)  # Set logging level to INFO

# Load environment variables from .env file
load_dotenv(override=True)  # override=True will overwrite existing environment variables
logging.info("Loaded environment variables")

# Initialize Weave for analytics/monitoring
weave.init("streamlit_sei")

# Global variables to track file download status across threads
download_started = False  # Flag to indicate when download has started
download_complete = False  # Flag to indicate when download is complete
download_error = None  # Store any error that occurs during download
download_thread = None  # Thread object for the download process
rerun_count = 0  # Counter used to create a visual loading indicator effect

def initialize_session_state():
    """
    Initialize the Streamlit session state with default values.
    Session state persists across reruns of the script.
    
    This function ensures all required state variables exist when the app starts
    or when a user refreshes the page, preventing errors from undefined variables.
    """
    if "messages" not in st.session_state:
        st.session_state['messages'] = []  # Store conversation history
    
    # Initialize download state variables
    if "download_complete" not in st.session_state:
        st.session_state["download_complete"] = False
    if "download_error" not in st.session_state:
        st.session_state["download_error"] = None
    if "download_started" not in st.session_state:
        st.session_state["download_started"] = False
    
    # Check if files already exist (in case of page refresh)
    # If the "processos" directory exists and contains files, assume download completed
    global download_complete
    if os.path.exists("processos") and os.listdir("processos"):
        st.session_state["download_complete"] = True
        download_complete = True

def background_download():
    """
    Download function that runs in a separate thread.
    Downloads and extracts a zip file from Google Drive without blocking the main thread.
    Updates global variables with the download status.
    
    The function attempts to download files containing SEI process data needed for the chatbot.
    Using a separate thread ensures the UI remains responsive during the download.
    """
    import os
    GDRIVE_FILE_ID = os.getenv('GDRIVE_FILE_ID')  # Get file ID from environment variables
    try:
        global download_complete, download_error
        # The hardcoded ID below is used instead of the environment variable (possible bug)
        success = download_and_extract_zip_from_drive("1H8KAkOmYcEk98YtWiufVHXFgPvdTnXbC")
        if success:
            download_complete = True
            logging.info("Download completed successfully and global variable set")
        else:
            download_error = "Download failed"
            logging.error("Download failed")
    except Exception as e:
        download_error = str(e)
        logging.error(f"Error during download: {e}")

def get_message(message_data) -> Optional[Tuple[str, str]]:
    """
    Process the message data from the AI stream and convert to a format usable by Streamlit.
    
    This function extracts messages from the AI agent's response stream and
    converts them to the role/content format needed by Streamlit's chat interface.
    
    Args:
        message_data: The message data dictionary from the agent's stream
        
    Returns:
        Tuple containing (role, content) or None if message should be skipped
    """
    message = message_data["messages"][-1]  # Get the last message from the data
    
    # Check message type and convert to appropriate role for Streamlit
    if isinstance(message, (HumanMessage, AIMessage, ToolMessage)):
        # Map message types to Streamlit roles: HumanMessage -> "user", others -> "assistant"
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        return role, message.content
    return None  # Return None for messages we don't want to process

def setup_agents():
    """
    Configure and return the MultiAgents setup.
    
    This function defines the AI models to be used for different agent roles.
    The supervisor agent (Llama 3.3) orchestrates the interaction while the
    main agent (Gemini) handles the actual responses to user queries.
    
    Returns:
        MultiAgents: An initialized MultiAgents object with configured models
    """
    # Configuration for different AI models
    models = {
        "supervisor": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.0  # 0.0 means deterministic/predictable outputs
        },
        "agent": {
            "provider": "google",
            "model": "gemini-2.0-flash-lite",
            "temperature": 0.0
        },
    }
    return MultiAgents(models)  # Initialize agents with the configured models

def should_display_message(content: str) -> bool:
    """
    Check if a message should be displayed in the chat interface.
    
    This function filters out internal system messages that shouldn't be shown to the user,
    such as agent-to-agent communications or status updates.
    
    Args:
        content: The message content to check
        
    Returns:
        Boolean indicating if the message should be displayed (True) or hidden (False)
    """
    skip_phrases = [
        "Successfully transferred",
        "transferred to",
        "transferred back"
    ]
    return not any(phrase in content for phrase in skip_phrases)

@st.fragment(run_every=1)  # Start a new Streamlit fragment that updates every second
def update_download_status():
    """
    Update the download status and manage the background download process.
    
    This fragment runs periodically to check if the download has completed or 
    encountered errors. It initiates the download thread if needed and 
    updates the UI to reflect the current download status.
    
    The @st.fragment decorator prevents this function from causing a full page rerun.
    """
    # Access global variables for thread management
    global download_thread, download_complete, download_error, rerun_count
    
    # Start the download in a background thread if not already started or completed
    if not st.session_state["download_complete"] and not st.session_state["download_started"]:
        # First time initialization - start the download thread
        st.session_state["download_started"] = True
        download_thread = threading.Thread(target=background_download)
        download_thread.daemon = True  # Thread will exit when main program exits
        download_thread.start()
        logging.info("Download thread started")
    
    # Check for download completion from the background thread
    if download_complete:
        st.session_state["download_complete"] = True
        st.success("✅ Arquivos necessários carregados com sucesso!")
        # Note: st.rerun() was commented out to prevent unnecessary page refreshes
    
    # Store any download errors in session state
    if download_error:
        st.session_state["download_error"] = download_error
    
    # Display download progress with animated dots
    if not st.session_state["download_complete"] and st.session_state["download_started"]:
        st.info(f"⏳ Baixando arquivos necessários. Você já pode começar a conversar enquanto isso{"." * (rerun_count)}")
    
    # Update the loading indicator by cycling through 0-3 dots
    rerun_count = (rerun_count + 1) % 4

def main():
    """
    Main function that sets up the Streamlit interface and handles the chat functionality.
    
    This function:
    1. Configures the page layout and title
    2. Initializes the session state and download process
    3. Sets up the AI agents
    4. Displays existing chat history
    5. Handles new user inputs and generates responses from the AI
    """
    # Page configuration and title
    st.title("💬 Chatbot SEI TRE-RN")
    st.caption((
        "Um chatbot para responder perguntas sobre processos no Sistema Eletrônico "
        "de Informações (SEI) do Tribunal Regional Eleitoral do Rio Grande do Norte (TRE-RN). "
        "Atualmente é possível responder perguntas como: "
        "\"O processo XXX/XXXX existe? \", "
        "\"Quantos documentos tem o processo XXX/XXXX?\", "
        "\"Quais são os documentos do tipo xxxxxx do processo XXX/XXXX?\" e "
        "\"Quais são os documentos de X a Y do processo XXX/XXXX?\""
    ))
    
    # Initialize session state variables
    initialize_session_state()
    
    # Start/update the download process and show status
    update_download_status()
    
    # Setup AI agents
    agents = setup_agents()
    
    # Display existing chat history from session state
    for msg in st.session_state['messages']:
        st.chat_message(msg["role"]).write(msg["content"])
    
    # Handle new user input
    prompt = st.chat_input()
    if prompt:
        # Add user message to chat history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # Add a warning if the download is still in progress
        if not st.session_state["download_complete"]:
            st.warning("O download dos arquivos ainda está em andamento. Algumas funcionalidades podem estar limitadas.")
        
        try:
            # Stream the AI response
            with st.spinner("Processando sua pergunta..."):
                # Call the AI agent with the current conversation history
                stream = agents.stream(
                    {"messages": st.session_state['messages']},
                    recursion_limit=25  # Limit recursion depth for safety
                    )
                
                # Add logging for debugging
                logging.info(f"Starting to process stream for prompt: {prompt[:30]}...")
                
                # Initialize assistant_content to store the final response
                assistant_content = None
                
                # Process each piece of the streamed response
                for stream_data in stream:
                    result = get_message(stream_data)
                    if result is None:
                        continue  # Skip messages we don't want to display
                    
                    role, content = result
                    logging.debug(f"Received message - Role: {role}, Content length: {len(content)}")
                    
                    # For assistant messages that should be displayed, update the UI
                    if role == "assistant" and should_display_message(content):
                        # Store the complete content (will be overwritten with each new chunk)
                        assistant_content = content
                        # Update the displayed message with current content
                        st.chat_message("assistant").markdown(assistant_content)
                
                # Only append the final complete response to session state history
                if assistant_content:
                    logging.info(f"Final response length: {len(assistant_content)}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                else:
                    logging.warning("No assistant content was generated!")
                    
        except Exception as e:
            # Handle and display any errors that occur during processing
            logging.error(f"Error during streaming: {str(e)}")
            st.error(f"Ocorreu um erro: {str(e)}")

# Entry point of the application
if __name__ == "__main__":
    main()