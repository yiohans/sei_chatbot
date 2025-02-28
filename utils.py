import os
import zipfile
import gdown
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread-local storage for session state updates
thread_local = threading.local()

def download_and_extract_zip_from_drive(file_id, output_dir="processos", session_state=None):
    """
    Download a public zip file from Google Drive using gdown and extract its contents.
    
    Args:
        file_id (str): The Google Drive file ID
        output_dir (str): Directory to extract contents to
        session_state: Optional Streamlit session state object
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Store session state reference in thread local storage if provided
    if session_state:
        thread_local.session_state = session_state
    
    # logger.info(f"Starting download of file ID: {file_id}")
    os.makedirs(output_dir, exist_ok=True)
    logger.debug(f"Created/verified output directory: {output_dir}")
    
    zip_path = os.path.join(output_dir, "downloaded_file.zip")
    
    try:
        # Download with gdown
        logger.info(f"Downloading file from Google Drive...")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, zip_path, quiet=True)
        logger.info(f"Download completed successfully to {zip_path}")
        
        # Extract the zip file
        logger.info(f"Extracting contents to {output_dir}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_count = len(zip_ref.namelist())
            logger.debug(f"Found {file_count} files in the archive")
            zip_ref.extractall(output_dir)
        logger.info(f"Extraction completed successfully")
            
        # Remove the zip file after extraction (optional)
        logger.debug(f"Removing temporary zip file: {zip_path}")
        os.remove(zip_path)
        logger.info(f"Process completed successfully")
        
        return True
    except zipfile.BadZipFile:
        logger.error(f"The downloaded file is not a valid ZIP archive")
        return False
    except Exception as e:
        logger.error(f"Error downloading or extracting file: {e}", exc_info=True)
        print(f"Error downloading or extracting file: {e}")
        return False