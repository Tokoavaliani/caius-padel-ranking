from abc import ABC, abstractmethod
from typing import List, Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from models import Player, Match, RatingChange
from datetime import datetime

# ----------------------------------------------------
# Contracts - what must be implemented for data access
# ----------------------------------------------------

class PlayerRepository(ABC):
    """
    Abstract interface for player data access.
    
    This is the "Repository Pattern" - it abstracts away database details.
    We can swap Supabase for MySQL, SQLite, MongoDB, or even a mock for testing.
    
    Follows the Dependency Inversion Principle: depend on abstractions, not concretions.
    """
    
    @abstractmethod
    def create(self, player: Player) -> Player:
        """Create a new player."""
        pass
    
    @abstractmethod
    def get_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Player]:
        """Get player by name."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Player]:
        """Get all players."""
        pass
    
    @abstractmethod
    def update(self, player: Player) -> Player:
        """Update player information."""
        pass
    
    @abstractmethod
    def delete(self, player_id: int) -> bool:
        """Delete a player."""
        pass


class MatchRepository(ABC):
    """Abstract interface for match data access."""
    
    @abstractmethod
    def create(self, match: Match) -> Match:
        """Create a new match record."""
        pass
    
    @abstractmethod
    def get_by_id(self, match_id: int) -> Optional[Match]:
        """Get match by ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Match]:
        """Get all matches."""
        pass
    
    @abstractmethod
    def get_by_player(self, player_id: int) -> List[Match]:
        """Get all matches for a player."""
        pass


class RatingHistoryRepository(ABC):
    """Abstract interface for rating history data access."""
    
    @abstractmethod
    def create(self, rating_change: RatingChange) -> RatingChange:
        """Record a rating change."""
        pass
    
    @abstractmethod
    def get_by_player(self, player_id: int, limit: int = 10) -> List[RatingChange]:
        """Get rating history for a player."""
        pass

# ----------------------------------------------------
# Supabase implementations
# ----------------------------------------------------

class SupabasePlayerRepository(PlayerRepository):
    """
    Supabase implementation of PlayerRepository.
    
    This class knows HOW to store data in Supabase,
    but doesn't know WHAT the data means or business rules.
    """
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def create(self, player: Player) -> Player:
        """Create new player in Supabase."""
        data = {
            'name': player.name,
            'current_elo': player.current_elo,
            'games_played': player.games_played,
            'wins': player.wins,
            'losses': player.losses
        }
        
        result = self.client.table('players').insert(data).execute()
        
        # Convert database row to Player object
        row = result.data[0]
        return Player(
            player_id=row['player_id'],
            name=row['name'],
            current_elo=row['current_elo'],
            games_played=row['games_played'],
            wins=row['wins'],
            losses=row['losses'],
            created_at=row.get('created_at')
        )
    
    def get_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        result = self.client.table('players').select('*').eq('player_id', player_id).execute()
        
        if not result.data:
            return None
        
        row = result.data[0]
        return Player(
            player_id=row['player_id'],
            name=row['name'],
            current_elo=row['current_elo'],
            games_played=row['games_played'],
            wins=row['wins'],
            losses=row['losses'],
            created_at=row.get('created_at')
        )
    
    def get_by_name(self, name: str) -> Optional[Player]:
        """Get player by name."""
        result = self.client.table('players').select('*').eq('name', name).execute()
        
        if not result.data:
            return None
        
        row = result.data[0]
        return Player(
            player_id=row['player_id'],
            name=row['name'],
            current_elo=row['current_elo'],
            games_played=row['games_played'],
            wins=row['wins'],
            losses=row['losses'],
            created_at=row.get('created_at')
        )
    
    def get_all(self) -> List[Player]:
        """Get all players ordered by rating."""
        result = self.client.table('players').select('*').order('current_elo', desc=True).execute()
        
        return [
            Player(
                player_id=row['player_id'],
                name=row['name'],
                current_elo=row['current_elo'],
                games_played=row['games_played'],
                wins=row['wins'],
                losses=row['losses'],
                created_at=row.get('created_at')
            )
            for row in result.data
        ]
    
    def update(self, player: Player) -> Player:
        """Update player information."""
        data = {
            'current_elo': player.current_elo,
            'games_played': player.games_played,
            'wins': player.wins,
            'losses': player.losses
        }
        
        result = self.client.table('players').update(data).eq('player_id', player.player_id).execute()
        
        row = result.data[0]
        return Player(
            player_id=row['player_id'],
            name=row['name'],
            current_elo=row['current_elo'],
            games_played=row['games_played'],
            wins=row['wins'],
            losses=row['losses'],
            created_at=row.get('created_at')
        )
    
    def delete(self, player_id: int) -> bool:
        """Delete a player."""
        self.client.table('players').delete().eq('player_id', player_id).execute()
        return True


class SupabaseMatchRepository(MatchRepository):
    """Supabase implementation of MatchRepository."""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def create(self, match: Match) -> Match:
        """Create new match record."""
        data = {
            'match_date': match.match_date,
            'team1_player1_id': match.team1_player1_id,
            'team1_player2_id': match.team1_player2_id,
            'team2_player1_id': match.team2_player1_id,
            'team2_player2_id': match.team2_player2_id,
            'team1_avg_rating_before': match.team1_avg_rating_before,
            'team2_avg_rating_before': match.team2_avg_rating_before,
            'winning_team': match.winning_team,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score
        }
        
        result = self.client.table('matches').insert(data).execute()
        row = result.data[0]
        
        return Match(
            match_id=row['match_id'],
            match_date=row['match_date'],
            team1_player1_id=row['team1_player1_id'],
            team1_player2_id=row['team1_player2_id'],
            team2_player1_id=row['team2_player1_id'],
            team2_player2_id=row['team2_player2_id'],
            team1_avg_rating_before=row['team1_avg_rating_before'],
            team2_avg_rating_before=row['team2_avg_rating_before'],
            winning_team=row['winning_team'],
            team1_score=row.get('team1_score'),
            team2_score=row.get('team2_score'),
            created_at=row.get('created_at')
        )
    
    def get_by_id(self, match_id: int) -> Optional[Match]:
        """Get match by ID."""
        result = self.client.table('matches').select('*').eq('match_id', match_id).execute()
        
        if not result.data:
            return None
        
        row = result.data[0]
        return Match(
            match_id=row['match_id'],
            match_date=row['match_date'],
            team1_player1_id=row['team1_player1_id'],
            team1_player2_id=row['team1_player2_id'],
            team2_player1_id=row['team2_player1_id'],
            team2_player2_id=row['team2_player2_id'],
            team1_avg_rating_before=row['team1_avg_rating_before'],
            team2_avg_rating_before=row['team2_avg_rating_before'],
            winning_team=row['winning_team'],
            team1_score=row.get('team1_score'),
            team2_score=row.get('team2_score'),
            created_at=row.get('created_at')
        )
    
    def get_all(self) -> List[Match]:
        """Get all matches."""
        result = self.client.table('matches').select('*').order('match_date', desc=True).execute()
        
        return [
            Match(
                match_id=row['match_id'],
                match_date=row['match_date'],
                team1_player1_id=row['team1_player1_id'],
                team1_player2_id=row['team1_player2_id'],
                team2_player1_id=row['team2_player1_id'],
                team2_player2_id=row['team2_player2_id'],
                team1_avg_rating_before=row['team1_avg_rating_before'],
                team2_avg_rating_before=row['team2_avg_rating_before'],
                winning_team=row['winning_team'],
                team1_score=row.get('team1_score'),
                team2_score=row.get('team2_score'),
                created_at=row.get('created_at')
            )
            for row in result.data
        ]
    
    def get_by_player(self, player_id: int) -> List[Match]:
        """Get all matches for a specific player."""
        # This is complex - player could be in any of 4 positions
        result = self.client.table('matches').select('*').or_(
            f'team1_player1_id.eq.{player_id},'
            f'team1_player2_id.eq.{player_id},'
            f'team2_player1_id.eq.{player_id},'
            f'team2_player2_id.eq.{player_id}'
        ).order('match_date', desc=True).execute()
        
        return [
            Match(
                match_id=row['match_id'],
                match_date=row['match_date'],
                team1_player1_id=row['team1_player1_id'],
                team1_player2_id=row['team1_player2_id'],
                team2_player1_id=row['team2_player1_id'],
                team2_player2_id=row['team2_player2_id'],
                team1_avg_rating_before=row['team1_avg_rating_before'],
                team2_avg_rating_before=row['team2_avg_rating_before'],
                winning_team=row['winning_team'],
                team1_score=row.get('team1_score'),
                team2_score=row.get('team2_score'),
                created_at=row.get('created_at')
            )
            for row in result.data
        ]


class SupabaseRatingHistoryRepository(RatingHistoryRepository):
    """Supabase implementation of RatingHistoryRepository."""
    
    def __init__(self, supabase_client: Client):
        self.client = supabase_client
    
    def create(self, rating_change: RatingChange) -> RatingChange:
        """Record a rating change."""
        data = {
            'player_id': rating_change.player_id,
            'match_id': rating_change.match_id,
            'old_rating': rating_change.old_rating,
            'new_rating': rating_change.new_rating,
            'rating_change': rating_change.rating_change
        }
        
        result = self.client.table('rating_history').insert(data).execute()
        row = result.data[0]
        
        return RatingChange(
            history_id=row['history_id'],
            player_id=row['player_id'],
            match_id=row['match_id'],
            old_rating=row['old_rating'],
            new_rating=row['new_rating'],
            rating_change=row['rating_change'],
            recorded_at=row.get('recorded_at')
        )
    
    def get_by_player(self, player_id: int, limit: int = 10) -> List[RatingChange]:
        """Get rating history for a player."""
        result = self.client.table('rating_history').select('*').eq(
            'player_id', player_id
        ).order('recorded_at', desc=True).limit(limit).execute()
        
        return [
            RatingChange(
                history_id=row['history_id'],
                player_id=row['player_id'],
                match_id=row['match_id'],
                old_rating=row['old_rating'],
                new_rating=row['new_rating'],
                rating_change=row['rating_change'],
                recorded_at=row.get('recorded_at')
            )
            for row in result.data
        ]