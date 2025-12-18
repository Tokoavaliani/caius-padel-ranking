from abc import ABC, abstractmethod
from typing import List, Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from models import Player, Match, RatingChange
from database import PlayerRepository, MatchRepository, RatingHistoryRepository
from elo_calculator import EloCalculator

class PadelEloPresenter:
    """
    Handles all presentation/display logic.
    
    Separates HOW we show data from WHAT data we show.
    Makes it easy to add different output formats (CLI, web, API, etc.)
    """
    
    @staticmethod
    def display_rankings(players: List[Player], title: str = "CURRENT RANKINGS"):
        """Display formatted rankings table."""
        if not players:
            print("No players found.")
            return
        
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}")
        print(f"{'Rank':<6} {'Player':<25} {'Elo':<8} {'Played':<8} {'W-L':<10} {'Win %':<8}")
        print(f"{'-'*80}")
        
        for idx, player in enumerate(players, 1):
            win_pct = player.win_rate * 100
            print(f"{idx:<6} {player.name:<25} {player.current_elo:<8} "
                  f"{player.games_played:<8} {player.wins}-{player.losses:<8} {win_pct:.1f}%")
        
        print(f"{'='*80}\n")

    @staticmethod
    def display_player_history(player: Player, history: List[RatingChange]):
        """Display player's rating history."""
        if not history:
            print(f"No match history found for {player.name}")
            return
        
        print(f"\n{'='*80}")
        print(f"RATING HISTORY FOR {player.name.upper()}")
        print(f"{'='*80}")
        print(f"{'Match ID':<10} {'Old':<8} {'New':<8} {'Change':<8} {'Date':<20}")
        print(f"{'-'*80}")
        
        for record in history:
            # print(record.recorded_at, type(record.recorded_at))
            change_sign = "+" if record.rating_change >= 0 else ""
            timestamp = record.recorded_at
            if timestamp:
                # Simple, safe formatting
                timestamp = timestamp.replace("T", " ")[:16]

            print(
                f"{record.match_id:<10} "
                f"{record.old_rating:<8} "
                f"{record.new_rating:<8} "
                f"{change_sign}{record.rating_change:<7} "
                f"{timestamp:<20}"
            )
        
        print(f"{'='*80}\n")