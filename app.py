import streamlit as st
import random
import time
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

# ================================================
# 🎨 PAGE CONFIGURATION
# ================================================
st.set_page_config(
    page_title="🤖 Smart RPS AI",
    page_icon="🎮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================================================
# 🎨 CUSTOM STYLING
# ================================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
        
        /* Main container styling */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Poppins', sans-serif;
        }
        
        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Title styling */
        h1 {
            text-align: center;
            color: #ffffff;
            font-weight: 800;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            margin-bottom: 0px;
            font-size: 3em !important;
        }
        
        h2, h3, h4 {
            color: #ffffff;
            text-align: center;
            font-weight: 600;
        }
        
        /* Card containers */
        .game-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
            margin: 20px 0;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        /* Button styling */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 15px;
            font-size: 18px;
            font-weight: 700;
            padding: 15px 0;
            width: 100%;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        div.stButton > button:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        div.stButton > button:active {
            transform: translateY(0px);
        }
        
        /* Result box styling */
        .result-box {
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            color: white;
            font-size: 22px;
            font-weight: 700;
            margin: 15px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
        
        /* Metric styling */
        [data-testid="stMetricValue"] {
            font-size: 2em;
            font-weight: 800;
            color: #667eea;
        }
        
        /* Info box */
        .strategy-tip {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3);
            margin: 20px 0;
        }
        
        /* Progress bar */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Subtitle */
        .subtitle {
            text-align: center;
            color: #ffffff;
            font-size: 1.2em;
            margin-bottom: 30px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }
        
        /* Stats header */
        .stats-header {
            color: #667eea;
            font-weight: 700;
            font-size: 1.5em;
            margin-bottom: 15px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# ================================================
# 🎯 GAME CONFIGURATION
# ================================================
MOVES = ["rock", "paper", "scissors"]
EMOJIS = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
COUNTERS = {"rock": "paper", "paper": "scissors", "scissors": "rock"}

# ================================================
# 💾 SESSION STATE INITIALIZATION
# ================================================


def initialize_session_state():
    """Initialize all session state variables"""
    if "move_history" not in st.session_state:
        st.session_state.move_history = {move: 0 for move in MOVES}

    if "scores" not in st.session_state:
        st.session_state.scores = {"player": 0, "ai": 0, "ties": 0}

    if "last_round" not in st.session_state:
        st.session_state.last_round = {
            "player": None, "ai": None, "result": None}

    if "game_log" not in st.session_state:
        st.session_state.game_log = []

    if "ai_strategy" not in st.session_state:
        st.session_state.ai_strategy = "adaptive"

    if "rounds_played" not in st.session_state:
        st.session_state.rounds_played = 0


initialize_session_state()

# ================================================
# 🧠 AI LOGIC
# ================================================


def predict_player_move(history, rounds_played):
    """Advanced AI prediction based on player history"""
    if rounds_played < 3:
        # Random strategy for first few rounds
        return random.choice(MOVES)

    total_moves = sum(history.values())
    if total_moves == 0:
        return random.choice(MOVES)

    # Weight recent moves more heavily
    if st.session_state.game_log:
        recent_moves = [round_data["player"]
                        for round_data in st.session_state.game_log[-5:]]
        if len(recent_moves) >= 3:
            # Check for patterns
            most_recent = recent_moves[-1]
            if recent_moves.count(most_recent) >= 2:
                return COUNTERS[most_recent]

    # Fallback to frequency-based prediction
    likely_player_move = max(history, key=history.get)

    # Add some randomness to avoid being too predictable
    if random.random() < 0.15:  # 15% random choice
        return random.choice(MOVES)

    return COUNTERS[likely_player_move]


def determine_winner(player_move, ai_move):
    """Determine the winner of the round"""
    if player_move == ai_move:
        return "tie"

    winning_combinations = {
        ("rock", "scissors"),
        ("paper", "rock"),
        ("scissors", "paper")
    }

    if (player_move, ai_move) in winning_combinations:
        return "player"
    return "ai"


def play_round(player_move):
    """Execute a game round"""
    # Update move history
    st.session_state.move_history[player_move] += 1
    st.session_state.rounds_played += 1

    # AI makes its choice
    ai_move = predict_player_move(
        st.session_state.move_history, st.session_state.rounds_played)

    # Determine winner
    result = determine_winner(player_move, ai_move)

    # Update scores
    if result == "tie":
        st.session_state.scores["ties"] += 1
        message = "🤝 It's a Tie!"
        color = "#9E9E9E"
    elif result == "player":
        st.session_state.scores["player"] += 1
        message = "🎉 You Win!"
        color = "#4CAF50"
    else:
        st.session_state.scores["ai"] += 1
        message = "🤖 AI Wins!"
        color = "#F44336"

    # Store round data
    st.session_state.last_round = {
        "player": player_move,
        "ai": ai_move,
        "result": message,
        "color": color
    }

    # Log the round
    st.session_state.game_log.append({
        "round": st.session_state.rounds_played,
        "player": player_move,
        "ai": ai_move,
        "winner": result,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })


def reset_game():
    """Reset all game state"""
    st.session_state.move_history = {move: 0 for move in MOVES}
    st.session_state.scores = {"player": 0, "ai": 0, "ties": 0}
    st.session_state.last_round = {"player": None, "ai": None, "result": None}
    st.session_state.game_log = []
    st.session_state.rounds_played = 0


# ================================================
# 🎮 HEADER SECTION
# ================================================
st.markdown("<h1>🪨📄✂️ SMART RPS AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Challenge an adaptive AI that learns from your patterns!</p>",
            unsafe_allow_html=True)

# ================================================
# 🎯 GAME CONTROLS
# ================================================
st.markdown("<div class='game-card'>", unsafe_allow_html=True)
st.markdown("<p class='stats-header'>🎯 Choose Your Move</p>",
            unsafe_allow_html=True)

cols = st.columns(3)
for idx, move in enumerate(MOVES):
    with cols[idx]:
        if st.button(f"{EMOJIS[move]}\n{move.upper()}", key=f"move_{move}"):
            with st.spinner("🤔 AI is thinking..."):
                time.sleep(0.8)
            play_round(move)
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ================================================
# 🔄 RESET BUTTON
# ================================================
st.markdown("<div class='game-card'>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 RESET GAME", key="reset"):
        reset_game()
        st.success("✅ Game reset successfully!")
        time.sleep(0.5)
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ================================================
# 🎮 LAST ROUND RESULTS
# ================================================
if st.session_state.last_round["player"]:
    st.markdown("<div class='game-card'>", unsafe_allow_html=True)
    st.markdown("<p class='stats-header'>🎮 Last Round</p>",
                unsafe_allow_html=True)

    player = st.session_state.last_round["player"]
    ai = st.session_state.last_round["ai"]
    result = st.session_state.last_round["result"]
    color = st.session_state.last_round["color"]

    st.markdown(f"""
        <div class='result-box' style='background: linear-gradient(135deg, {color} 0%, {color}dd 100%);'>
            <div style='font-size: 3em; margin-bottom: 10px;'>
                {EMOJIS[player]} VS {EMOJIS[ai]}
            </div>
            <div style='font-size: 1.1em; opacity: 0.9;'>
                You: <b>{player.upper()}</b> | AI: <b>{ai.upper()}</b>
            </div>
            <div style='margin-top: 15px; font-size: 1.3em;'>
                {result}
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='game-card'>", unsafe_allow_html=True)
    st.info("🎲 Make your first move to start the game!")
    st.markdown("</div>", unsafe_allow_html=True)

# ================================================
# 📊 SCOREBOARD
# ================================================
st.markdown("<div class='game-card'>", unsafe_allow_html=True)
st.markdown("<p class='stats-header'>📊 Live Scoreboard</p>",
            unsafe_allow_html=True)

scores = st.session_state.scores
total_games = sum(scores.values()) or 1

# Win rates
player_rate = round((scores["player"] / total_games) * 100, 1)
ai_rate = round((scores["ai"] / total_games) * 100, 1)
tie_rate = round((scores["ties"] / total_games) * 100, 1)

# Display win rate
st.markdown(f"**🏆 Your Win Rate: {player_rate}%**")
st.progress(player_rate / 100)

st.markdown("<br>", unsafe_allow_html=True)

# Score metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("👤 Player", scores["player"], delta=f"{player_rate}%")
with col2:
    st.metric("🤖 AI", scores["ai"], delta=f"{ai_rate}%")
with col3:
    st.metric("🤝 Ties", scores["ties"], delta=f"{tie_rate}%")

st.markdown("</div>", unsafe_allow_html=True)

# ================================================
# 📈 MOVE HISTORY VISUALIZATION
# ================================================
if st.session_state.rounds_played > 0:
    st.markdown("<div class='game-card'>", unsafe_allow_html=True)
    st.markdown("<p class='stats-header'>📈 Your Move Analysis</p>",
                unsafe_allow_html=True)

    fig, ax = plt.subplots(figsize=(10, 5))

    moves_data = list(st.session_state.move_history.values())
    colors = ['#667eea', '#764ba2', '#f093fb']

    bars = ax.bar(MOVES, moves_data, color=colors,
                  edgecolor='white', linewidth=2)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax.set_xlabel('Move Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Times Played', fontsize=12, fontweight='bold')
    ax.set_title('Your Move Frequency Pattern',
                 fontsize=14, fontweight='bold', pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("</div>", unsafe_allow_html=True)

# ================================================
# 📜 GAME LOG
# ================================================
if len(st.session_state.game_log) > 0:
    st.markdown("<div class='game-card'>", unsafe_allow_html=True)
    st.markdown("<p class='stats-header'>📜 Recent Game History</p>",
                unsafe_allow_html=True)

    # Show last 5 rounds
    # Reverse to show newest first
    recent_games = st.session_state.game_log[-5:][::-1]

    df = pd.DataFrame(recent_games)
    df['player'] = df['player'].apply(lambda x: f"{EMOJIS[x]} {x.upper()}")
    df['ai'] = df['ai'].apply(lambda x: f"{EMOJIS[x]} {x.upper()}")
    df['winner'] = df['winner'].apply(
        lambda x: "👤 Player" if x == "player" else "🤖 AI" if x == "ai" else "🤝 Tie")

    st.dataframe(
        df[['round', 'player', 'ai', 'winner', 'timestamp']].rename(columns={
            'round': 'Round',
            'player': 'Your Move',
            'ai': 'AI Move',
            'winner': 'Winner',
            'timestamp': 'Time'
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ================================================
# 💡 STRATEGY TIPS
# ================================================
st.markdown("""
    <div class='strategy-tip'>
        <h3 style='margin-top: 0; color: white;'>💡 Pro Strategy Tips</h3>
        <p style='margin-bottom: 0; font-size: 1.05em; line-height: 1.6;'>
            🧠 <b>The AI learns from your patterns!</b> It tracks your most frequent moves and recent choices.<br>
            🎯 <b>Stay unpredictable</b> - Mix up your strategy to keep the AI guessing.<br>
            🔄 <b>Break patterns</b> - If you notice you're losing, try changing your approach!<br>
            📊 <b>Study your stats</b> - Use the move analysis to see if you're becoming predictable.
        </p>
    </div>
""", unsafe_allow_html=True)

# ================================================
# 📱 FOOTER
# ================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
    <div style='text-align: center; color: white; opacity: 0.8; font-size: 0.9em;'>
        <p>Built with ❤️ using Streamlit | AI-Powered Rock-Paper-Scissors</p>
    </div>
""", unsafe_allow_html=True)
