import subprocess
import logging

from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

from tools import *

class MultiAgents:
    """
    A class that implements a multi-agent system using LangGraph for SEI (Sistema Eletrônico de Informações) chatbot.
    This system combines multiple specialist agents under a supervisor to handle user queries about SEI processes.
    """
    def __init__(self, models):
        """
        Initialize the MultiAgents system with the specified models configuration.
        
        Args:
            models: Dictionary containing configuration for supervisor and agent models
                   Each should specify provider, model name, and temperature
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize the language models for supervisor and agents
        self.supervisor_model, self.agent_model = self.initialize_models(models)
        
        # Commented out chat agent - left for potential future implementation
        # self.chat_agent = self.initialize_agent(
        #     name="chat_agent",
        #     tools=[],
        #     prompt="You can only chat with the user."
        # )
        
        # Initialize the research agent with SEI-specific tools
        self.research_agent = self.initialize_agent(
            name="sei_research_agent",
            # Equipping the agent with tools to search processes and retrieve documents
            tools=[search_process, get_document_list_from_process, get_document_by_type],
            prompt=(
                "Você é especialista em obter informações sobre processos do SEI. "
                "Você é capaz de: "
                "pesquisar processos usando a função search_process, "
                "listar documentos de um processo usando a função get_document_list_from_process, "
                "e obter tipos específicos de documentos de um processo usando a função get_document_by_type. "
            )
        )
        
        # Initialize the LangGraph workflow with a supervisor that manages the agents
        self.graph = self.initialize_graph((
            "Você é um chatbot com um time de especialistas para atender o usuário. "
            "Use sei_research_agent para responder perguntas sobre processos no "
            "Sistema Eletrônico de Informações (SEI) do TRE do Rio Grande do Norte (TRE-RN). "
            "Lembre que o usuário NÃO CONSEGUE LER as mensagens dos agentes, portanto, "
            "ORGANIZE, FORMATE e REPITA as informações relevantes que os especialistas fornecerem e escreva "
            "respostas claras e concisas para o usuário."
        ))

    def initialize_models(self, models):
        """
        Initialize the language models for both supervisor and agents based on provided configuration.
        Supports three providers: Groq, Ollama, and Google Generative AI.
        
        Args:
            models: Dictionary with 'supervisor' and 'agent' configurations
            
        Returns:
            tuple: (supervisor_model, agent_model)
        """
        # Select and initialize supervisor model based on provider
        match models['supervisor']["provider"]:
            case "groq":
                self.logger.info("Using Groq model for supervisor")
                llm_supervisor = ChatGroq(
                    model=models['supervisor']['model'],
                    temperature=models['supervisor']['temperature']
                )
            case "ollama":
                self.logger.info("Using Ollama model for supervisor")
                llm_supervisor = ChatOllama(
                    model=models['supervisor']['model'],
                    temperature=models['supervisor']['temperature']
                    )
                # For Ollama, we need to pull the model first
                model_name = models['supervisor']['model']
                subprocess.run(["ollama", "pull", model_name])
            case "google":
                self.logger.info("Using Google Generative AI model for supervisor")
                llm_supervisor = ChatGoogleGenerativeAI(
                    model=models['supervisor']['model'],
                    temperature=models['supervisor']['temperature']
                )
        
        # Select and initialize agent model based on provider        
        match models['agent']['provider']:
            case "groq":
                self.logger.info("Using Groq model for agent")
                llm_agent = ChatGroq(
                    model=models['agent']['model'],
                    temperature=models['agent']['temperature']
                )
            case "ollama":
                self.logger.info("Using Ollama model for agent")
                llm_agent = ChatOllama(
                    model=models['agent']['model'],
                    temperature=models['agent']['temperature']
                    )
                # For Ollama, we need to pull the model first
                model_name = models['agent']['model']
                subprocess.run(["ollama", "pull", model_name])
            case "google":
                self.logger.info("Using Google Generative AI model for agent")
                llm_agent = ChatGoogleGenerativeAI(
                    model=models['agent']['model'],
                    temperature=models['agent']['temperature']
                )
                
        return llm_supervisor, llm_agent
    
    def initialize_agent(self, name, prompt, tools):
        """
        Create a ReAct agent with specified name, prompt, and tools.
        
        Args:
            name: Name identifier for the agent
            prompt: Instructions for the agent's behavior and capabilities
            tools: List of functions the agent can use
            
        Returns:
            Agent object configured for the specified task
        """
        self.logger.info((
            f"Initializing agent: {name} with prompt:\n \"{prompt}\"\n"
            f"and tools: \n{tools}"
            ))
        agent = create_react_agent(
            self.agent_model,
            name=name,
            tools=tools,
            prompt=prompt,
        )
        return agent
    
    def initialize_graph(self, prompt):
        """
        Initialize the LangGraph workflow with the supervisor and agents.
        
        Args:
            prompt: Instructions for the supervisor on how to coordinate the agents
            
        Returns:
            Compiled LangGraph workflow ready for execution
        """
        self.logger.info(f"Initializing graph with supervisor prompt:\n\"{prompt}\"")
        workflow = create_supervisor(
            [self.research_agent],  # List of agents the supervisor will coordinate
            model=self.supervisor_model,
            prompt=prompt,
            output_mode="last_message"  # Only return the final response to the user
        )
        return workflow.compile()
    
    def run(self, messages, recursion_limit=10):
        """
        Execute the multi-agent system synchronously with the given messages.
        
        Args:
            messages: List of message dictionaries (user inputs)
            recursion_limit: Maximum number of agent-supervisor interactions
            
        Returns:
            Final response from the system
        """
        self.logger.info(f"Running MultiAgents with messages:\n{messages}")
        return self.graph.invoke(
            messages,
            {"recursion_limit": recursion_limit}
        )
    
    def stream(self, messages, recursion_limit=10):
        """
        Execute the multi-agent system asynchronously, streaming results as they become available.
        
        Args:
            messages: List of message dictionaries (user inputs)
            recursion_limit: Maximum number of agent-supervisor interactions
            
        Returns:
            Generator yielding intermediate values during execution
        """
        self.logger.info(f"Streaming MultiAgents with messages:\n{messages}")
        return self.graph.stream(
            messages,
            {"recursion_limit": recursion_limit},
            stream_mode="values"  # Stream the content values as they're generated
        )
