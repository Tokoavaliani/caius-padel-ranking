import streamlit as st
from database import SupabasePlayerRepository, SupabaseMatchRepository, SupabaseRatingHistoryRepository
from models import Player, Match, RatingChange
from services import PadelEloService
from elo_calculator import EloCalculator
from supabase import create_client
import os
from dotenv import load_dotenv
import pandas as pd
from auth import admin_login
from datetime import date as dt_date

st.set_page_config(page_title="Padel Elo Leaderboard", layout="wide")

# load environment variables
load_dotenv()

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]

# Initialize Supabase client
supabase = create_client(url, key)

# Initialize repositories
player_repo = SupabasePlayerRepository(supabase)
match_repo = SupabaseMatchRepository(supabase)
history_repo = SupabaseRatingHistoryRepository(supabase)

# Initialize Elo calculator and service
elo_calculator = EloCalculator(k_factor=32)
service = PadelEloService(player_repo, match_repo, history_repo, elo_calculator)

# ================================
# Streamlit functions
# ================================

def show_leaderboard():
    st.title("🏆 Caius Padel Power Rankings")

    players =player_repo.get_all()

    if not players:
        st.info("No players yet")
        return
    
    else:
        # Convert data to a format suitable for Streamlit table
        leaderboard_data = [
            {
                "Rank": idx,
                "Player": player.name,
                "Elo Rating": player.current_elo,
                "Played": player.games_played,
                "Wins": player.wins,
                "Losses": player.losses,
                "Win %": f"{player.win_rate*100:.1f}%"
            }
            for idx, player in enumerate(players, start=1)
        ]

        df = pd.DataFrame(leaderboard_data)

        st.dataframe(
            df.style
            .set_properties(**{"text-align": "center"})
            .background_gradient(subset=["Elo Rating"], cmap="Greens")
            .set_properties(subset=["Elo Rating"], **{"font-weight": "bold", "font-size": "110%"}),
            hide_index=True, 
            use_container_width=True
        )

def show_add_player():
    if not st.session_state.get("is_admin"):
        st.error("Admin access required")
        return

    st.title("➕ Add Player")

    with st.form("add_player_form"):
        name = st.text_input("Player name")
        submitted = st.form_submit_button("Add player")

    if submitted:
        if not name.strip():
            st.error("Player name cannot be empty")
            return

        try:
            player = service.add_player(name=name)
            st.success(f"✅ {player.name} added (Elo {player.current_elo})")
        except ValueError as e:
            # Friendly message instead of traceback
            st.warning(f"⚠️ {e}")

def show_add_match():
    if not st.session_state.get("is_admin"):
        st.error("Admin access required")
        return

    st.title("🎯 Add Match")

    players = player_repo.get_all()
    if len(players) < 4:
        st.warning("At least 4 players required")
        return

    player_map = {p.name: p.player_id for p in players}
    names = ["Select a player..."] + list(player_map.keys())

    with st.form("add_match_form"):
        st.subheader("Team 1")
        t1p1 = st.selectbox("Player 1", names, key="t1p1")
        t1p2 = st.selectbox("Player 2", names, key="t1p2")

        st.subheader("Team 2")
        t2p1 = st.selectbox("Player 1", names, key="t2p1")
        t2p2 = st.selectbox("Player 2", names, key="t2p2")

        winning_team = 1 if st.radio("Winning team", ["Team 1", "Team 2"]) == "Team 1" else 2
        match_date = st.date_input("Match date", value=dt_date.today(), max_value=dt_date.today())
        submitted = st.form_submit_button("Record match")

    if submitted:
        try:
            # All validation happens in the service
            match = service.record_match(
                team1_player1_name=t1p1,
                team1_player2_name=t1p2,
                team2_player1_name=t2p1,
                team2_player2_name=t2p2,
                winning_team=winning_team,
                match_date=match_date.isoformat()
            )
            # Success message with summary
            match_summary_html = f"""
            <div style="
                background-color:#d4edda;
                color:#155724;
                padding:15px;
                border-radius:5px;
                border:1px solid #c3e6cb;
                margin-bottom:10px;
            ">
            <b>✅ Match recorded successfully!</b><br><br>
            <b>Team 1:</b> {t1p1} & {t1p2}<br>
            <b>Team 2:</b> {t2p1} & {t2p2}<br>
            <b>Winner:</b> {'Team 1' if winning_team == 1 else 'Team 2'}🏆<br>
            <b>Date Played:</b> {match_date}
            </div>
            """

            st.markdown(match_summary_html, unsafe_allow_html=True)
        except ValueError as e:
            st.warning(f"⚠️ {e}")

# ================================
# Streamlit UI
# ================================

admin_login()

st.sidebar.title("Menu")

if st.session_state.get("is_admin"):
    st.markdown(
        "<span style='color: green; font-weight: bold;'>👑 ADMIN MODE</span>",
        unsafe_allow_html=True
    )

menu_options = ["Leaderboard"]

if st.session_state.get("is_admin"):
    menu_options += ["Add Player", "Record Match"]

selection = st.sidebar.radio("Go to", menu_options)

if selection == "Leaderboard":
    show_leaderboard()

elif selection == "Add Player":
    show_add_player()

elif selection == "Record Match":
    show_add_match()