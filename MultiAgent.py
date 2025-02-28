import subprocess
import logging

from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

from tools import *

class MultiAgents:
    def __init__(self, models):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.supervisor_model, self.agent_model = self.initialize_models(models)
        # self.chat_agent = self.initialize_agent(
        #     name="chat_agent",
        #     tools=[],
        #     prompt="You can only chat with the user."
        # )
        self.research_agent = self.initialize_agent(
            name="sei_research_agent",
            tools=[search_process, get_document_list_from_process, get_document_by_type],
            prompt=(
                "Você é especialista em obter informações sobre processos do SEI. "
                "Você é capaz de: "
                "pesquisar processos usando a função search_process, "
                "listar documentos de um processo usando a função get_document_list_from_process, "
                "e obter tipos específicos de documentos de um processo usando a função get_document_by_type. "
            )
        )
        self.graph = self.initialize_graph((
            "Você é um chatbot com um time de especialistas para atender o usuário. "
            "Use sei_research_agent para responder perguntas sobre processos no "
            "Sistema Eletrônico de Informações (SEI) do TRE do Rio Grande do Norte (TRE-RN). "
            "Lembre que o usuário NÃO CONSEGUE LER as mensagens dos agentes, portanto, "
            "ORGANIZE, FORMATE e REPITA as informações relevantes que os especialistas fornecerem e escreva "
            "respostas claras e concisas para o usuário."
        ))

    def initialize_models(self, models):
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
                model_name = models['supervisor']['model']
                subprocess.run(["ollama", "pull", model_name])
            case "google":
                self.logger.info("Using Google Generative AI model for supervisor")
                llm_supervisor = ChatGoogleGenerativeAI(
                    model=models['supervisor']['model'],
                    temperature=models['supervisor']['temperature']
                )
                
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
                model_name = models['agent']['model']
                subprocess.run(["ollama", "pull", model_name])
            case "google":
                self.logger.info("Using Google Generative AI model for agent")
                llm_agent = ChatGoogleGenerativeAI(
                    model=models['agent']['model'],
                    temperature=models['agent']['temperature']
                )
                
        return llm_supervisor, llm_agent
