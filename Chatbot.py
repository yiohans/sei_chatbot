import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import weave
from typing import Optional, Tuple

from MultiAgent import MultiAgents

import logging, os
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv(
    override=True
)

logging.info("Loaded environment variables")
logging.info(f"GROQ_API_KEY: {os.getenv('GROQ_API_KEY')}")
logging.info(f"WANDB_API_KEY: {os.getenv('WANDB_API_KEY')}")

# Initialize Weave
weave.init("streamlit_sei")

def initialize_session_state():
    """Initialize the session state with a welcome message."""
    if "messages" not in st.session_state:
        st.session_state['messages'] = [
            # {
            #     "role": "assistant",
            #     "content": "Olá! Como posso ajudar você com o Sistema Eletrônico de Informações (SEI)?"
            # }
        ]

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
        "Hoje é possível responder perguntas como: "
        " \"O processo XXX/XXXX existe? \", "
        " \"Quais são os documentos do processo XXX/XXXX?\" "
        " e \"Quais documentos do tipo xxxxxx do processo XXX/XXXX?\""
        ))
    
    # Initialize session state
    initialize_session_state()
    
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
        
        try:
            # Stream the response
            with st.spinner("Processando sua pergunta..."):
                stream = agents.stream(
                    {"messages": st.session_state['messages']},
                    recursion_limit=25
                    )
                
                # Create a placeholder for the assistant's message
                message_placeholder = st.chat_message("assistant")
                full_response = ""
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