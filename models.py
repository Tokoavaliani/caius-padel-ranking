import os
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from dotenv import load_dotenv
from dataclasses import dataclass

@dataclass
class Player:
    """ Represent a single player in the ranking system. """
    player_id: Optional[int] # this syntax is saying that player_id is an optional integer but can be none
    name: str
    current_elo: int
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    created_at: Optional[datetime] = None

    @property
    def win_rate(self) -> float:
        """ Calculate win percentage """
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played
    
    def __Str__(self) -> str:
        return f"{self.name} (ELO: {self.current_elo}, Wins: {self.wins}, Losses: {self.losses}, Win Rate: {self.win_rate:.2%})"
    
@dataclass
class Match:
    """ Represent a single doubles match of padel """
    match_id: Optional[int]
    match_date: str
    team1_player1_id: int
    team1_player2_id: int
    team2_player1_id: int
    team2_player2_id: int
    team1_avg_rating_before: int
    team2_avg_rating_before: int
    winning_team: int
    team1_score: Optional[int] = None
    team2_score: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class RatingChange:
    """ Represent a rating change event used to track history and for undo functionality """
    history_id: Optional[int]
    player_id: int
    match_id: int
    old_rating: int
    new_rating: int
    rating_change: int
    recorded_at: Optional[str] = None