# Load environment variables before importing modules that initialize API clients
from dotenv import load_dotenv
import os
load_dotenv()

from agents.companion import run_session_loop
from tools.memory_tools import setup_database

if __name__ == '__main__':
    # Ensure the database structure is created before starting
    setup_database() 
    
    # Start the conversation
    run_session_loop()