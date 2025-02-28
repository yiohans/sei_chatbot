import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import weave
from typing import Optional, Tuple
import threading
import time
import os

from MultiAgent import MultiAgents
from utils import download_and_extract_zip_from_drive

import logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv(override=True)
logging.info("Loaded environment variables")

# Initialize Weave
weave.init("streamlit_sei")

# Global variables for download status
download_complete = False
download_error = None
download_thread = None

def initialize_session_state():
    """Initialize the session state with a welcome message."""
    if "messages" not in st.session_state:
        st.session_state['messages'] = []
    
    # Initialize download state
    if "download_complete" not in st.session_state:
        st.session_state["download_complete"] = False
    if "download_error" not in st.session_state:
        st.session_state["download_error"] = None
    if "download_started" not in st.session_state:
        st.session_state["download_started"] = False
    
    # Check if files already exist (in case of page refresh)
    if os.path.exists("processos") and os.listdir("processos"):
        st.session_state["download_complete"] = True

def background_download():
    """Run the download in a background thread without accessing Streamlit context"""
    import os
    GDRIVE_FILE_ID = os.getenv('GDRIVE_FILE_ID')
    try:
        global download_complete, download_error
        success = download_and_extract_zip_from_drive(GDRIVE_FILE_ID, output_dir="processos")
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
    Process the message and return a tuple of (role, content).
    
    Args:
        message_data: The message data from the stream
        
    Returns:
        Tuple containing (role, content) or None if message should be skipped
    """
    message = message_data["messages"][-1]
    
    if isinstance(message, (HumanMessage, AIMessage, ToolMessage)):
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        return role, message.content
    return None

def setup_agents():
    """Configure and return the MultiAgents setup."""
    models = {
        "supervisor": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.0
        },
        "agent": {
            "provider": "google",
            "model": "gemini-2.0-flash-lite",
            "temperature": 0.0
        },
    }
    return MultiAgents(models)

def should_display_message(content: str) -> bool:
    """
    Check if the message should be displayed in the chat.
    """
    skip_phrases = [
        "Successfully transferred",
        "transferred to",
        "transferred back"
    ]
    return not any(phrase in content for phrase in skip_phrases)

def main():
    # Page configuration
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
    
    # Initialize session state
    initialize_session_state()
    
    # Start the download in a background thread if not already completed
    global download_thread, download_complete
    if not st.session_state["download_complete"] and not st.session_state["download_started"]:
        st.session_state["download_started"] = True
        download_thread = threading.Thread(target=background_download)
        download_thread.daemon = True
        download_thread.start()
        logging.info("Download thread started")
    
    # Check for download completion
    # This explicit check ensures we detect completion from the background thread
    if download_complete:
        st.session_state["download_complete"] = True
        logging.info("Main thread detected download completion")
    if download_error:
        st.session_state["download_error"] = download_error
    
    # Force refresh every few seconds while downloading
    if not st.session_state["download_complete"] and st.session_state["download_started"]:
        # This creates an invisible element that changes every second to trigger reruns
        st.empty().text(f"Checking download status... {time.time()}")
        time.sleep(1)
        st.rerun()
    
    # Display download status
    if not st.session_state["download_complete"]:
        st.sidebar.info("⏳ Baixando arquivos necessários... Você já pode começar a conversar enquanto isso.")
        if st.session_state.get("download_error"):
            st.sidebar.error(f"Erro no download: {st.session_state['download_error']}")
    else:
        st.sidebar.success("✅ Arquivos necessários carregados com sucesso!")
    
    # Setup agents
    agents = setup_agents()
    
    # Display chat history
    for msg in st.session_state['messages']:
        st.chat_message(msg["role"]).write(msg["content"])
    
    # Handle user input
    if prompt := st.chat_input():
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # Add a warning if the download is still in progress
        if not st.session_state["download_complete"]:
            st.warning("O download dos arquivos ainda está em andamento. Algumas funcionalidades podem estar limitadas.")
        
        try:
            # Stream the response
            with st.spinner("Processando sua pergunta..."):
                stream = agents.stream(
                    {"messages": st.session_state['messages']},
                    recursion_limit=25
                    )
                
                # Create a placeholder for the assistant's message
                message_placeholder = st.chat_message("assistant")
                assistant_content = ""
                
                # Add logging for debugging
                logging.info(f"Starting to process stream for prompt: {prompt[:30]}...")
                
                for stream_data in stream:
                    result = get_message(stream_data)
                    if result is None:
                        continue
                    
                    role, content = result
                    logging.debug(f"Received message - Role: {role}, Content length: {len(content)}")
                    
                    if role == "assistant" and should_display_message(content):
                        # For assistant messages, always use the latest complete chunk
                        # This prevents partial messages from being displayed
                        assistant_content = content
                        # Update the displayed message with complete content
                        message_placeholder.markdown(assistant_content)
                
                # Only append the final response to session state
                if assistant_content:
                    logging.info(f"Final response length: {len(assistant_content)}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                else:
                    logging.warning("No assistant content was generated!")
                    
        except Exception as e:
            logging.error(f"Error during streaming: {str(e)}")
            st.error(f"Ocorreu um erro: {str(e)}")

if __name__ == "__main__":
    main()