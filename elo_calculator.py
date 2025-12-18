import os
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from dotenv import load_dotenv
from dataclasses import dataclass

class EloCalculator:
    """ Pure Elo calculation logic """
    def __init__(self, k_factor: int = 32):
        """ Initialise calculator with K-factor """
        if k_factor <= 0:
            raise ValueError("K-factor must be a positive integer")
        self.k_factor = k_factor

    def expected_score(self, rating_a: int, rating_b: int) -> float:
        """ Calculate expected score for team A against team B """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def calculate_rating_change(self, current_rating: float, opponent_rating: float, actual_score: float) -> float:
        """ Calculate the change in rating after a match """
        expected_score = self.expected_score(current_rating, opponent_rating)
        return self.k_factor * (actual_score - expected_score)
    
    def calculate_team_rating(self, player1_rating: int, player2_rating: int) -> float:
        """ Calculate team rating as average of two players' rating """
        return (player1_rating + player2_rating) / 2
    
    def calculate_match_outcome(self, team1_player1_rating: int, team1_player2_rating: int, team2_player1_rating: int, team2_player2_rating: int, team1_won: bool) -> dict:
        """ Calculate rating changes for all players in a match"""
        # calculate team rating averages
        team1_rating = self.calculate_team_rating(team1_player1_rating, team1_player2_rating)
        team2_rating = self.calculate_team_rating(team2_player1_rating, team2_player2_rating)

        # calculate expected scores
        team1_expected = self.expected_score(team1_rating, team2_rating)
        team2_expected = 1 - team1_expected

        # determine actual scores
        team1_actual = 1.0 if team1_won else 0.0
        team2_actual = 1.0 - team1_actual

        team1_change = self.calculate_rating_change(team1_rating, team2_rating, team1_actual)
        team2_change = self.calculate_rating_change(team2_rating, team1_rating, team2_actual)

        info = {
            'team1_rating': team1_rating,
            'team2_rating': team2_rating,
            'team1_expected': team1_expected,
            'team2_expected': team2_expected,
            'team1_change': team1_change,
            'team2_change': team2_change
        }
        return info