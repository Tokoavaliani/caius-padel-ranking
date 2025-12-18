import os
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# load environment variables from .env file
# This keeps credentials secure and out of code

load_dotenv()

class PadelEloSystem:
    """ 
    Main class for managing the ranking system.
    
    Handles:
    - Database connection to Supabase
    - Player management (adding, retrieving players)
    - Match recording and ELO calculation
    - Rankings retrieval

    Attributes:
    - supabase client for database operations
    - k_factor for how much ratings change per match
    - initial_rating default starting ELO rating for new players
    """
    def __init__(self, k_factor: int = 32, initial_rating: int = 1500):
        """ 
        Initialise the ELO system and connect to database
        """

        # Get Supabase credentials from environment variables
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        # Validate that credintials are present
        if not url or not key:
            raise ValueError("Supabase URL and KEY must be set in .env file")
        
        # Create Supabase client - connection to database
        self.supabase: Client = create_client(url, key)
        self.k_factor = k_factor
        self.initial_rating = initial_rating

        print(f"Connected to Supabase successfully.")
        print(f"K-factor set to {self.k_factor}, Initial rating: {self.initial_rating}")