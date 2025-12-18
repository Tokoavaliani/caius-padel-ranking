import os
#from dotenv import load_dotenv
import streamlit as st
from supabase import create_client

from elo_calculator import EloCalculator
from database import (
    SupabasePlayerRepository,
    SupabaseMatchRepository,
    SupabaseRatingHistoryRepository
)
from services import PadelEloService
from presentation import PadelEloPresenter

def create_supabase_client():
    # load_dotenv()
    
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")
    
    return create_client(url, key)


def main():
    # ------------------------------------------------------------------
    # Infrastructure setup
    # ------------------------------------------------------------------
    supabase = create_supabase_client()
    
    player_repo = SupabasePlayerRepository(supabase)
    match_repo = SupabaseMatchRepository(supabase)
    history_repo = SupabaseRatingHistoryRepository(supabase)
    
    elo_calculator = EloCalculator(k_factor=32)
    
    service = PadelEloService(
        player_repo=player_repo,
        match_repo=match_repo,
        history_repo=history_repo,
        elo_calculator=elo_calculator,
        initial_rating=1500
    )
    
    presenter = PadelEloPresenter()
    
    # ------------------------------------------------------------------
    # Example usage
    # ------------------------------------------------------------------
    try:
        service.add_player("Haris")
        service.add_player("Toko")
        service.add_player("Kofi")
        service.add_player("Zara")
    except ValueError:
        pass  # Players already exist
    
    service.record_match(
        team1_player1_name="Haris",
        team1_player2_name="Toko",
        team2_player1_name="Kofi",
        team2_player2_name="Zara",
        winning_team=1,
        match_date="2025-12-17",
        team1_score="6-4 6-4",
        team2_score="4-6 4-6"
    )
    
    rankings = service.get_rankings()
    presenter.display_rankings(rankings)
    
    haris = service.get_player("Haris")
    history = service.get_player_history("Haris")
    presenter.display_player_history(haris, history)


if __name__ == "__main__":
    main()