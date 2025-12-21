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
from datetime import datetime, timedelta
import altair as alt

st.set_page_config(page_title="Caius Padel", layout="wide")

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
    st.markdown(
        f"""
        <div style="
            font-size: 1rem;
            color: #495057;
        ">
            Last updated {datetime.today().strftime('%d %B %Y')}
        </div>
        """,
        unsafe_allow_html=True
    )
    st.divider()

    players = player_repo.get_all()

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

        player_map = {p.player_id: p.name for p in players}
        names = ["Select a player..."] + list(player_map.values())

        search_query = st.selectbox("Search Player...", names, index=0, key="search_player")

        df = pd.DataFrame(leaderboard_data)

        st.dataframe(
            df.style
            .set_properties(**{"text-align": "center"})
            .background_gradient(subset=["Elo Rating"], cmap="Greens")
            .set_properties(subset=["Elo Rating"], **{"font-weight": "bold", "font-size": "110%"}),
            hide_index=True, 
            use_container_width=True
        )

        if search_query != "Select a player...":
            query_df = df[df["Player"].str.contains(search_query, case=False, na=False)]
            player = player_repo.get_by_name(search_query)

            # Get rating history for this player
            rating_history = history_repo.get_by_player(player.player_id)

            if query_df.empty:
                st.warning(f"No data found for '{search_query}'")
            else:
                st.markdown(f"### Player Analytics for *{search_query}*:")

                # 5️⃣ Show filtered player row in table
                st.dataframe(
                    query_df.style
                    .set_properties(**{"text-align": "center"})
                    .set_properties(subset=["Elo Rating"], **{"font-weight": "bold", "font-size": "110%"}),
                    hide_index=True,
                    use_container_width=True
                )

                # Key Metrics in Dashboard form
                col1, col2, col3, col4, col5, col6 = st.columns(6)

                col1.metric("Rank", query_df.iloc[0]["Rank"])
                col2.metric("Elo Rating", player.current_elo, delta=rating_history[-1].rating_change if rating_history else 0)
                col3.metric("Games Played", player.games_played)
                col4.metric("Wins", player.wins)
                col5.metric("Losses", player.losses)
                col6.metric("Win %", round(player.win_rate * 100, 2))

                st.divider()

                # Top partners
                matches = match_repo.get_by_player(player.player_id) # all matches involving this player
                partners = {}

                for match in matches:
                    if player.player_id in [match.team1_player1_id, match.team1_player2_id]:
                        team = [match.team1_player1_id, match.team1_player2_id]
                        win = (match.winning_team == 1)
                    else:
                        team = [match.team2_player1_id, match.team2_player2_id]
                        win = (match.winning_team == 2)

                    partner = (set(team) - {player.player_id}).pop()  # get the other player
                    if partner not in partners:
                        partners[partner] = {"games": 0, "wins": 0}

                    partners[partner]["games"] += 1
                    if win:
                        partners[partner]["wins"] += 1

                partner_stats = [
                    {
                    "Partner Name": player_map[partner_id],
                    "Games Played": stats['games'],
                    "Wins": stats['wins'],
                    "Win %": stats['wins']/stats['games']
                    }
                    for partner_id, stats in partners.items()
                ]

                partner_stats_df = pd.DataFrame(partner_stats).sort_values(by="Win %", ascending=False).reset_index(drop=True)

                st.markdown("## Top Partners")

                cols = st.columns(2)
                with cols[0].container(border=True):
                    "### Most Frequent Partnerships"

                    st.altair_chart(
                        alt.Chart(partner_stats_df)
                        .mark_arc()
                        .encode(
                            alt.Theta("Games Played:Q"),
                            alt.Color("Partner Name:N").title("Partner"),
                        )
                        .configure_legend(orient="bottom"),
                        use_container_width=True
                    )

                with cols[1].container(border=True):
                    "### Most Successful Partnerships"

                    st.altair_chart(
                        alt.Chart(partner_stats_df)
                        .mark_bar()
                        .encode(
                            x=alt.X("Partner Name:N", 
                                    title="Partner",
                                    sort=alt.SortField(
                                    field="Win %",
                                    order="descending"
                                )),
                            y=alt.Y(
                                "Win %:Q",
                                title="Win Rate",
                                axis=alt.Axis(format=".0%")
                            ),
                            tooltip=[
                                alt.Tooltip("Partner Name:N"),
                                alt.Tooltip("Win %:Q", format=".2%")
                            ]
                        ),
                        use_container_width=True
                    )

                # Rating over time
                cols = st.columns([7, 3])
                with cols[0]:
                    "### Elo Rating History"
                    selected_period = st.pills(
                        "Time Period", ["All Time", "6m", "3m", "7d"], default="All Time", selection_mode="single"
                    )

                    # Player comparison
                    all_players = player_repo.get_all()
                    other_players = [p for p in all_players if p.player_id != player.player_id]
                    compare_with = st.multiselect(
                        "Compare with other players",
                        options=[p.name for p in other_players],
                        default=[]
                    )

                    if rating_history:
                        # order by recorded_at
                        rating_history = sorted(rating_history, key=lambda r: r.recorded_at)
                        # Get all matches to map match_id -> actual match date
                        all_matches = match_repo.get_all()
                        match_date_map = {m.match_id: pd.to_datetime(m.match_date) for m in all_matches}
                        
                        # Get histories for all selected players
                        all_histories = []
                        
                        # Current player's history
                        first_match_date = match_date_map.get(rating_history[0].match_id, pd.to_datetime('today'))
                        
                        history_data = [
                            {
                                "Player": player.name,
                                "Match Number": 0,
                                "Rating": 1500,
                                "Change": 0,
                                "Match Date": first_match_date - pd.Timedelta(days=1)  # Day before first match
                            }
                        ] + [
                            {
                                "Player": player.name,
                                "Match Number": idx + 1,
                                "Rating": record.new_rating,
                                "Change": record.rating_change,
                                "Match Date": match_date_map.get(record.match_id, pd.to_datetime(record.recorded_at))
                            }
                            for idx, record in enumerate(rating_history)
                        ]
                        all_histories.extend(history_data)

                        # Add comparison players
                        if compare_with:
                            for compare_name in compare_with:
                                compare_player = next(p for p in all_players if p.name == compare_name)
                                compare_history = history_repo.get_by_player(compare_player.player_id)
                                
                                if compare_history:
                                    compare_history = sorted(compare_history, key=lambda r: r.recorded_at)
                                    first_match_date = match_date_map.get(compare_history[0].match_id, pd.to_datetime('today'))
                                    
                                    compare_data = [
                                        {
                                            "Player": compare_name,
                                            "Match Number": 0,
                                            "Rating": 1500,
                                            "Change": 0,
                                            "Match Date": first_match_date - pd.Timedelta(days=1)
                                        }
                                    ] + [
                                        {
                                            "Player": compare_name,
                                            "Match Number": idx + 1,
                                            "Rating": record.new_rating,
                                            "Change": record.rating_change,
                                            "Match Date": match_date_map.get(record.match_id, pd.to_datetime(record.recorded_at))
                                        }
                                        for idx, record in enumerate(compare_history)
                                    ]
                                    all_histories.extend(compare_data)

                        # Create DataFrame
                        history_df = pd.DataFrame(all_histories)
                        history_df['Match Date'] = pd.to_datetime(history_df['Match Date'])

                        # Apply time filter on Match Date
                        if selected_period != "All Time":
                            today = datetime.now()
                            
                            if selected_period == "7d":
                                cutoff = today - timedelta(days=7)
                            elif selected_period == "3m":
                                cutoff = today - timedelta(days=90)
                            elif selected_period == "6m":
                                cutoff = today - timedelta(days=180)
                            
                            history_df = history_df[history_df['Match Date'] >= cutoff]

                        if history_df.empty:
                            st.info(f"No data for {selected_period}")
                        else:
                            # Create fixed color scale - main player always gets first color
                            all_player_names = [player.name] + compare_with
                            color_scale = alt.Scale(
                                domain=all_player_names,
                                range=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
                            )
                            
                            # Chart with Match Number on x-axis
                            chart = alt.Chart(history_df).mark_line(point=True).encode(
                                x=alt.X('Match Number:Q', title='Match Number', axis=alt.Axis(format='d')),  # 'd' = integer format
                                y=alt.Y('Rating:Q', title='Elo Rating', scale=alt.Scale(zero=False)),
                                color=alt.Color('Player:N', legend=alt.Legend(title="Player"), scale=color_scale),
                                tooltip=[
                                    alt.Tooltip('Player:N', title='Player'),
                                    alt.Tooltip('Match Number:Q', title='Match #', format='d'),
                                    alt.Tooltip('Match Date:T', format='%b %d, %Y', title='Date'),
                                    alt.Tooltip('Rating:Q', title='Rating'),
                                    alt.Tooltip('Change:Q', title='Change')
                                ]
                            ).properties(
                                height=400
                            )
                            
                            st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("No rating history yet")

                with cols[1]:
                    "### Raw Data"

                    st.dataframe(partner_stats_df.style.format({"Win %": "{:.2%}"}), use_container_width=True, hide_index=True)

                st.divider()

def show_matches():
    st.title("📅 Matches")
    st.markdown(
        f"""
        <div style="
            font-size: 1rem;
            color: #495057;
        ">
            Last updated {datetime.today().strftime('%d %B %Y')}
        </div>
        """,
        unsafe_allow_html=True
    )
    st.divider()

    matches = match_repo.get_all()

    if not matches:
        st.info("No Matches Yet")
        return
    
    else:
        # Convert data to a format suitable for Streamlit table
        matches_data = [
            {
                "Match Date": datetime.strptime( match.match_date, "%Y-%m-%d").date().strftime("%d %b %Y"),
                "Winning Team": (
                    f"{player_repo.get_by_id(getattr(match, f'team{match.winning_team}_player1_id')).name} & "
                    f"{player_repo.get_by_id(getattr(match, f'team{match.winning_team}_player2_id')).name}"
                ),
                "Losing Team": (
                    f"{player_repo.get_by_id(getattr(match, f'team{3 - match.winning_team}_player1_id')).name} & "
                    f"{player_repo.get_by_id(getattr(match, f'team{3 - match.winning_team}_player2_id')).name}"
                ),
                "Score": match.match_score
            }
            for idx, match in enumerate(matches, start=1)
        ]

        df = pd.DataFrame(matches_data).sort_values("Match Date", ascending=False)

        st.dataframe(
            df.style
            .set_properties(**{"text-align": "center"}),
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

    player_map = {p.player_id: p.name for p in players}
    names = ["Select a player..."] + list(player_map.values())

    with st.form("add_match_form"):
        col1, col2, col3 = st.columns([19, 2, 19])
        with col1:
            st.subheader("Team 1:")
            t1p1 = st.selectbox("Player 1", names, key="t1p1")
            t1p2 = st.selectbox("Player 2", names, key="t1p2")
            t1_score = st.number_input(
                "Team 1 Score (Optional)",
                min_value=0,
                step=1,
                format="%d"
            )

        with col3:
            st.subheader("Team 2:")
            t2p1 = st.selectbox("Player 1", names, key="t2p1")
            t2p2 = st.selectbox("Player 2", names, key="t2p2")
            t2_score = st.number_input(
                "Team 2 Score (Optional)",
                min_value=0,
                step=1,
                format="%d"
            )

        winning_team = 1 if st.radio("Winning team", ["Team 1", "Team 2"]) == "Team 1" else 2
        match_date = st.date_input("Match date", value=dt_date.today(), max_value=dt_date.today())
        submitted = st.form_submit_button("Record match")

    if submitted:
        if t1_score == 0 and t2_score == 0:
            t1_score = None
            t2_score = None
        try:
            # All validation happens in the service
            match = service.record_match(
                team1_player1_name=t1p1,
                team1_player2_name=t1p2,
                team2_player1_name=t2p1,
                team2_player2_name=t2p2,
                winning_team=winning_team,
                match_date=match_date.isoformat(),
                team1_score=t1_score,
                team2_score=t2_score
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
            <b>Score:</b> {match.match_score}<br>
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
    st.sidebar.markdown(
        "<span style='color: green; font-weight: bold;'>👑 ADMIN MODE</span>",
        unsafe_allow_html=True
    )

menu_options = ["Leaderboard", "Matches"]

if st.session_state.get("is_admin"):
    menu_options += ["Add Player", "Record Match"]

selection = st.sidebar.radio("Go to", menu_options)

if selection == "Leaderboard":
    show_leaderboard()

elif selection == "Matches":
    show_matches()

elif selection == "Add Player":
    show_add_player()

elif selection == "Record Match":
    show_add_match()