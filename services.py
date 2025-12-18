from abc import ABC, abstractmethod
from typing import List, Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from models import Player, Match, RatingChange
from database import PlayerRepository, MatchRepository, RatingHistoryRepository
from elo_calculator import EloCalculator

class PadelEloService:
    """
    Service layer that orchestrates business operations.
    
    This is the "glue" that connects:
    - Domain models (Player, Match)
    - Business logic (EloCalculator)
    - Data access (Repositories)
    
    Follows the Service Pattern: encapsulates business workflows.
    """
    
    def __init__(
        self,
        player_repo: PlayerRepository,
        match_repo: MatchRepository,
        history_repo: RatingHistoryRepository,
        elo_calculator: EloCalculator,
        initial_rating: int = 1500
    ):
        self.player_repo = player_repo
        self.match_repo = match_repo
        self.history_repo = history_repo
        self.elo_calculator = elo_calculator
        self.initial_rating = initial_rating
    
    def add_player(self, name: str) -> Player:
        """
        Add a new player with initial rating.
        
        Business rule: New players start at initial_rating.
        """
        # Check if player exists
        existing = self.player_repo.get_by_name(name)
        if existing:
            raise ValueError(f"Player '{name}' already exists")
        
        # Create new player
        player = Player(
            player_id=None,
            name=name,
            current_elo=self.initial_rating,
            games_played=0,
            wins=0,
            losses=0
        )
        
        return self.player_repo.create(player)
    
    def get_player(self, name: str) -> Optional[Player]:
        """Get player by name."""
        return self.player_repo.get_by_name(name)
    
    def get_rankings(self, limit: int = 10) -> List[Player]:
        """Get top players by rating."""
        all_players = self.player_repo.get_all()
        return all_players[:limit]
    
    def record_match(
        self,
        team1_player1_name: str,
        team1_player2_name: str,
        team2_player1_name: str,
        team2_player2_name: str,
        winning_team: int,
        match_date: str,
        team1_score: Optional[str] = None,
        team2_score: Optional[str] = None
    ) -> Match:
        """
        Record a match and update all ratings.
        
        This is a complex workflow that:
        1. Validates all inputs
        2. Retrieves all players
        3. Calculates rating changes (using EloCalculator)
        4. Updates player records
        5. Creates match record
        6. Records rating history
        
        Returns the created Match object.
        """
        # Validate winning team
        if winning_team not in [1, 2]:
            raise ValueError("winning_team must be 1 or 2")
        
        # Check for duplicate players in the same match
        all_players = [team1_player1_name, team1_player2_name, team2_player1_name, team2_player2_name]
        if len(set(all_players)) < 4:
            raise ValueError("A player cannot appear twice in the same match")

        # Get all players
        team1_p1 = self.player_repo.get_by_name(team1_player1_name)
        team1_p2 = self.player_repo.get_by_name(team1_player2_name)
        team2_p1 = self.player_repo.get_by_name(team2_player1_name)
        team2_p2 = self.player_repo.get_by_name(team2_player2_name)

        # Validate all players exist
        missing = [name for name, player in zip(all_players, [team1_p1, team1_p2, team2_p1, team2_p2]) if player is None]
        if missing:
            raise ValueError(f"Players not found: {', '.join(missing)}")
        
        # Calculate rating changes using EloCalculator
        outcome = self.elo_calculator.calculate_match_outcome(
            team1_p1.current_elo,
            team1_p2.current_elo,
            team2_p1.current_elo,
            team2_p2.current_elo,
            team1_won=(winning_team == 1)
        )
        
        # Create match record
        match = Match(
            match_id=None,
            match_date=match_date,
            team1_player1_id=team1_p1.player_id,
            team1_player2_id=team1_p2.player_id,
            team2_player1_id=team2_p1.player_id,
            team2_player2_id=team2_p2.player_id,
            team1_avg_rating_before=round(outcome['team1_rating']),
            team2_avg_rating_before=round(outcome['team2_rating']),
            winning_team=winning_team,
            team1_score=team1_score,
            team2_score=team2_score
        )
        
        created_match = self.match_repo.create(match)
        
        # Update all players
        team1_won = (winning_team == 1)
        players_to_update = [
            (team1_p1, outcome['team1_change'], team1_won),
            (team1_p2, outcome['team1_change'], team1_won),
            (team2_p1, outcome['team2_change'], not team1_won),
            (team2_p2, outcome['team2_change'], not team1_won)
        ]
        
        for player, rating_change, won in players_to_update:
            old_rating = player.current_elo
            new_rating = round(old_rating + rating_change)
            
            # Update player stats
            player.current_elo = new_rating
            player.games_played += 1
            if won:
                player.wins += 1
            else:
                player.losses += 1
            
            # Save to database
            self.player_repo.update(player)
            
            # Record history
            history = RatingChange(
                history_id=None,
                player_id=player.player_id,
                match_id=created_match.match_id,
                old_rating=old_rating,
                new_rating=new_rating,
                rating_change=round(rating_change)
            )
            self.history_repo.create(history)
        
        return created_match
    
    def get_player_history(self, name: str, limit: int = 10) -> List[RatingChange]:
        """Get rating history for a player."""
        player = self.player_repo.get_by_name(name)
        if not player:
            raise ValueError(f"Player '{name}' not found")
        
        return self.history_repo.get_by_player(player.player_id, limit)
