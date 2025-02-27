import os
from typing import Optional
import json

def search_process(id: str) -> str:
    """
    Procura uma pasta de processo SEI no sistema de arquivos.

    Use esta função para localizar documentos de processos administrativos pelo seu número de referência.
    A função lida com formatos de ID tradicionais (XXX/YYYY) e compactos (XXXYYYY).

    Args:
        id (str): Número do processo em qualquer formato:
            - Formato separado: "XXX/YYYY"
            - Formato compacto: "XXXYYYY"
            O número será automaticamente preenchido com zeros à esquerda se necessário.

    Returns:
        str: Um dos seguintes:
            - Nome da pasta se o processo existir
            - None se o processo não for encontrado
            - "Process not found" se o processo não for encontrado (formato separado ou erros)
    """
    root_path = os.path.dirname(__file__)
    processes_path = os.path.join(root_path, "processos")
    # print(f"Processes path: {processes_path}")
    try:
        if len(id) < 9:
            if id.find("/") == -1:
                id = id.zfill(9)
            else:
                id = id.split("/")
                id[0] = id[0].zfill(5)
                id[1] = id[1]
                id = "/".join(id)
        if id.find("/") == -1:
            folder = f"SEI_{id[:-4]}_{id[-4:]}"
            # print(f"Searching for {folder}")
            if os.path.exists(os.path.join(processes_path, folder)):
                # print(f"Process {id} found!")
                return folder
            else:
                # print(f"Process {id} not found!")
                return "Process not found"
        else:
            folder = f"SEI_{id.split('/')[0]}_{id.split('/')[1]}"
            # print(f"Searching for {folder}")
            if os.path.exists(os.path.join(processes_path, folder)):
                # print(f"Process {id} found!")
                return folder
            else:
                # print(f"Process {id} not found!")
                return "Process not found"
    except Exception as e:
        print(f"Error: {e}")
        return "Process not found"

def get_document_list_from_process(
    parameters: str
) -> list[str]:
    """
    Recupera documentos PDF de uma pasta de processo SEI com suporte a paginação.

    Use esta função para obter uma lista de documentos PDF dentro de uma pasta de processo.
    Os resultados podem ser paginados usando parâmetros de limite e deslocamento.
    Normalmente usado após localizar uma pasta de processo com search_process().

    Args:
        parameters (str): Uma string contendo o nome da pasta do processo e parâmetros de paginação.
            A string deve ser formatada da seguinte forma:
            "process_id,limit,offset"
            - process_id: O número do processo
            - limit: O número máximo de documentos a retornar
            - offset: O número de documentos a pular

    Returns:
        Union[dict(str : list[str], str : int), str]: Um dos seguintes:
            - Um dicionário contendo:
                - "documents": Uma lista de nomes de documentos PDF
                - "total_number_of_documents": O número total de documentos na pasta
            - "Invalid parameters" se a string de entrada não estiver formatada corretamente
            - "Process folder not found" se a pasta do processo não existir
    """
    try:
        process_id, limit, offset = parameters.split(",")
        process_folder = search_process(process_id)
        if process_folder == "Process not found" or process_folder == "Process folder not found":
            return process_folder
        limit = int(limit)
        offset = int(offset)
    except Exception as e:
        print(f"Error: {e}")
        return "Invalid parameters"
    try:
        root_path = os.path.dirname(__file__)
        tree = os.walk(os.path.join(root_path, "processos", process_folder))
        documents = []
        for root, dirs, files in tree:
            documents.extend([
                file
                for file in files
                if file.endswith(".pdf")
                ])
        documents.sort()
        return {
            "documents" : documents[offset:offset+limit],
            "total_number_of_documents" : len(documents)
        }
    except Exception as e:
        print(f"Error: {e}")
        return "Process folder not found"

def read_doc(file_path: str) -> Optional[str]:
    """
    Lê um documento PDF e extrai seu conteúdo de texto.

    Args:
        file_path (str): O caminho para o arquivo PDF.

    Returns:
        Optional[str]: O texto extraído do PDF, ou None se ocorrer um erro.
    """
    from PyPDF2 import PdfReader
    try:
        reader = PdfReader(file_path)
        contents = []
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            contents.append(page.extract_text())
        return "\n".join(contents)
    except Exception as e:
        return f"Error: {e}"
    
def get_document_by_type(parameters : str) -> str:
    """
    Obtem uma lista de documentos por tipo de um processo SEI.
    
    Args:
        parameters (str): Uma string contendo o ID do processo e tipo de documento.
            A string deve ser formatada da seguinte forma:
            "process_id,document_type"
            - process_id: O ID do processo (ex: "XXX/YYYY" ou "XXXYYYY") 
            - document_type: O tipo de documento a ser procurado
    """
    process_id , document_type = parameters.split(",")
    process_folder = search_process(process_id)
    if process_folder == "Process not found" or process_folder == "Process folder not found":
        return process_folder
    response = get_document_list_from_process(f"{process_id},1,0")
    try:
        total_documents = response["total_number_of_documents"]
    except Exception as e:
        print(f"Error: {e}")
        return "Error: Could not retrieve total number"
    response = get_document_list_from_process(f"{process_id},{total_documents},0")
    documents = response["documents"]
    documents_found = [
        document
        for document in documents
        if document_type.lower() in document.lower()
    ]
    if len(documents_found) > 0:
        return {
            "documents" : documents_found,
            "number_of_documents" : len(documents_found)
        }
    else:
        return f"Documents of type {document_type} not found in process {process_id}"
            
    