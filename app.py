import streamlit as st
import random
import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter

st.set_page_config(
    page_title="NEXUS · RPS ENGINE",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
MOVES = ["rock", "paper", "scissors"]

EMOJIS = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

COLORS = {"rock": "#fb923c", "paper": "#60a5fa", "scissors": "#f472b6"}

COUNTERS = {"rock": "paper", "paper": "scissors", "scissors": "rock"}

AI_STRATEGY_LABELS = {
    "frequency":  "Frequency Analysis",
    "markov":     "Markov Chain",
    "adaptive":   "Adaptive Ensemble",
    "aggressive": "Aggressive Counter",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════


def init_state():
    defaults = {
        "scores": {"player": 0, "ai": 0, "ties": 0},
        "move_freq": {m: 0 for m in MOVES},
        "game_log": [],
        "last_round": None,
        "rounds": 0,
        "current_streak": 0,
        "best_win_streak": 0,
        "ai_strategy": "adaptive",
        "markov": {m: {n: 0 for n in MOVES} for m in MOVES},
        "prev_player_move": None,
        "ai_confidence": 0.0,
        "ai_predicted": None,
        "pattern_warning": None,
        "achievements": set(),
        "new_achievement": None,
        "show_debug": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()
s = st.session_state

# ═══════════════════════════════════════════════════════════════════════════════
#  AI ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class AIEngine:
    @staticmethod
    def strategy_frequency(freq, rounds):
        if rounds < 2:
            return random.choice(MOVES), 0.33
        total = sum(freq.values()) or 1
        probs = {m: freq[m] / total for m in MOVES}
        predicted = max(probs, key=probs.get)
        return COUNTERS[predicted], probs[predicted]

    @staticmethod
    def strategy_markov(markov, prev_move, rounds):
        if rounds < 4 or prev_move is None:
            return random.choice(MOVES), 0.33
        transitions = markov[prev_move]
        total = sum(transitions.values()) or 1
        probs = {m: transitions[m] / total for m in MOVES}
        predicted = max(probs, key=probs.get)
        return COUNTERS[predicted], probs[predicted]

    @staticmethod
    def strategy_pattern(game_log, window=6):
        if len(game_log) < window:
            return random.choice(MOVES), 0.33
        recent = [r["player_move"] for r in game_log[-window:]]
        for pat_len in [2, 3]:
            if len(recent) >= pat_len * 2:
                pattern = recent[-pat_len:]
                for i in range(len(recent) - pat_len * 2 + 1):
                    if recent[i:i+pat_len] == pattern:
                        following = []
                        for j in range(len(recent) - pat_len):
                            if recent[j:j+pat_len] == pattern and j + pat_len < len(recent):
                                following.append(recent[j+pat_len])
                        if following:
                            cnt = Counter(following)
                            predicted = cnt.most_common(1)[0][0]
                            conf = cnt.most_common(1)[0][1] / len(following)
                            return COUNTERS[predicted], conf
        return random.choice(MOVES), 0.33

    @staticmethod
    def strategy_aggressive(freq, game_log, rounds):
        if rounds < 3:
            return random.choice(MOVES), 0.33
        recent_moves = [r["player_move"]
                        for r in game_log[-8:]] if game_log else []
        if not recent_moves:
            return random.choice(MOVES), 0.33
        cnt = Counter(recent_moves)
        predicted = cnt.most_common(1)[0][0]
        confidence = cnt.most_common(1)[0][1] / len(recent_moves)
        return COUNTERS[predicted], min(confidence + 0.1, 0.99)

    @classmethod
    def get_move(cls, strategy, state):
        freq = state["move_freq"]
        markov = state["markov"]
        prev = state["prev_player_move"]
        log = state["game_log"]
        rounds = state["rounds"]

        if strategy == "frequency":
            counter, conf = cls.strategy_frequency(freq, rounds)
        elif strategy == "markov":
            counter, conf = cls.strategy_markov(markov, prev, rounds)
        elif strategy == "aggressive":
            counter, conf = cls.strategy_aggressive(freq, log, rounds)
        else:
            results = [
                cls.strategy_frequency(freq, rounds),
                cls.strategy_markov(markov, prev, rounds),
                cls.strategy_pattern(log),
                cls.strategy_aggressive(freq, log, rounds),
            ]
            vote_weight = {m: 0.0 for m in MOVES}
            for move, conf in results:
                vote_weight[move] += conf
            counter = max(vote_weight, key=vote_weight.get)
            conf = vote_weight[counter] / sum(vote_weight.values())

        predicted = {v: k for k, v in COUNTERS.items()}.get(counter)
        return counter, conf, predicted

# ═══════════════════════════════════════════════════════════════════════════════
#  GAME LOGIC
# ═══════════════════════════════════════════════════════════════════════════════


def determine_result(player, ai):
    if player == ai:
        return "tie"
    if (player, ai) in {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}:
        return "win"
    return "lose"


def play_round(player_move):
    if s.prev_player_move is not None:
        s.markov[s.prev_player_move][player_move] += 1

    ai_move, confidence, ai_predicted = AIEngine.get_move(
        s.ai_strategy,
        {"move_freq": s.move_freq, "markov": s.markov,
         "prev_player_move": s.prev_player_move, "game_log": s.game_log, "rounds": s.rounds}
    )

    result = determine_result(player_move, ai_move)
    s.scores[{"win": "player", "lose": "ai", "tie": "ties"}[result]] += 1

    if result == "win":
        s.current_streak = s.current_streak + 1 if s.current_streak >= 0 else 1
        s.best_win_streak = max(s.best_win_streak, s.current_streak)
    elif result == "lose":
        s.current_streak = s.current_streak - 1 if s.current_streak <= 0 else -1
    else:
        s.current_streak = 0

    s.move_freq[player_move] += 1
    s.rounds += 1

    s.last_round = {
        "player_move": player_move, "ai_move": ai_move,
        "result": result, "confidence": confidence,
        "ai_predicted": ai_predicted, "round_no": s.rounds,
    }
    s.game_log.append({
        "round": s.rounds, "player_move": player_move, "ai_move": ai_move,
        "result": result, "confidence": round(confidence * 100, 1),
        "ts": datetime.now().strftime("%H:%M:%S"),
    })

    s.ai_confidence = confidence
    s.ai_predicted = ai_predicted
    s.prev_player_move = player_move
    _update_pattern_warning()
    _check_achievements()


def _update_pattern_warning():
    if s.rounds < 6:
        s.pattern_warning = None
        return
    recent = [r["player_move"] for r in s.game_log[-8:]]
    cnt = Counter(recent)
    top_move, top_cnt = cnt.most_common(1)[0]
    if top_cnt / len(recent) > 0.65:
        s.pattern_warning = f"You've played {EMOJIS[top_move]} {top_move.upper()} {top_cnt}x in last {len(recent)} rounds. AI has likely adapted."
    else:
        s.pattern_warning = None


def _check_achievements():
    achv = s.achievements
    new = None
    if s.rounds == 1 and "first_blood" not in achv:
        achv.add("first_blood")
        new = ("⚔️", "FIRST BLOOD", "Played your first round")
    if s.rounds == 10 and "ten_rounds" not in achv:
        achv.add("ten_rounds")
        new = ("🔟", "DECADE", "Survived 10 rounds")
    if s.best_win_streak >= 5 and "streak_5" not in achv:
        achv.add("streak_5")
        new = ("🔥", "ON FIRE", "5-win streak achieved")
    if s.best_win_streak >= 10 and "streak_10" not in achv:
        achv.add("streak_10")
        new = ("💥", "UNSTOPPABLE", "10-win streak — legendary")
    if s.scores["player"] >= 25 and "veteran" not in achv:
        achv.add("veteran")
        new = ("🎖️", "VETERAN", "25 total wins")
    if s.rounds >= 50 and "endurance" not in achv:
        achv.add("endurance")
        new = ("🏃", "ENDURANCE", "Played 50 rounds")
    total = s.scores["player"] + s.scores["ai"]
    if total > 0 and s.scores["player"] / total > 0.7 and s.rounds >= 10 and "dominator" not in achv:
        achv.add("dominator")
        new = ("👑", "DOMINATOR", ">70% win rate over 10+ rounds")
    s.new_achievement = new


def reset_game():
    keys = ["scores", "move_freq", "game_log", "last_round", "rounds", "current_streak",
            "best_win_streak", "markov", "prev_player_move", "ai_confidence", "ai_predicted",
            "pattern_warning", "achievements", "new_achievement"]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    init_state()

# ═══════════════════════════════════════════════════════════════════════════════
#  CHARTS
# ═══════════════════════════════════════════════════════════════════════════════


def chart_win_timeline():
    if len(s.game_log) < 3:
        return None
    fig, ax = plt.subplots(figsize=(10, 3))
    log = s.game_log
    rounds = [r["round"] for r in log]
    cumwin, cumlose, cw, cl = [], [], 0, 0
    for r in log:
        if r["result"] == "win":
            cw += 1
        if r["result"] == "lose":
            cl += 1
        cumwin.append(cw)
        cumlose.append(cl)
    ax.fill_between(rounds, cumwin, alpha=0.15, color="#4ade80")
    ax.fill_between(rounds, cumlose, alpha=0.15, color="#f87171")
    ax.plot(rounds, cumwin, color="#4ade80", linewidth=2, label="Player Wins")
    ax.plot(rounds, cumlose, color="#f87171", linewidth=2, label="AI Wins")
    ax.set_xlabel("Round")
    ax.set_ylabel("Cumulative")
    ax.legend()
    ax.grid(True, alpha=0.4)
    plt.tight_layout()
    return fig


def chart_move_distribution():
    if s.rounds < 1:
        return None
    fig, ax = plt.subplots(figsize=(6, 3))
    values = [s.move_freq[m] for m in MOVES]
    bar_colors = [COLORS[m] for m in MOVES]
    labels = [f"{EMOJIS[m]} {m.upper()}" for m in MOVES]
    bars = ax.bar(labels, values, color=bar_colors, width=0.55)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    str(val), ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_ylim(0, max(values)*1.3+1)
    ax.yaxis.set_visible(False)
    plt.tight_layout()
    return fig


def chart_ai_confidence():
    if len(s.game_log) < 3:
        return None
    fig, ax = plt.subplots(figsize=(10, 2.5))
    rounds = [r["round"] for r in s.game_log]
    confs = [r["confidence"] for r in s.game_log]
    ax.fill_between(rounds, confs, alpha=0.12, color="#63cab7")
    ax.plot(rounds, confs, color="#63cab7", linewidth=1.5)
    ax.axhline(50, color="#aaa", linewidth=1, linestyle="--")
    ax.set_ylim(0, 100)
    ax.set_xlabel("Round")
    ax.set_ylabel("Confidence %")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def chart_result_donut():
    scores = s.scores
    if sum(scores.values()) < 1:
        return None
    fig, ax = plt.subplots(figsize=(4, 4))
    sizes = [scores["player"], scores["ai"], scores["ties"]]
    colors = ["#4ade80", "#f87171", "#a78bfa"]
    wedges, _ = ax.pie(sizes, colors=colors, startangle=90,
                       wedgeprops={"linewidth": 0, "width": 0.55})
    total = sum(sizes) or 1
    win_pct = round(scores["player"] / total * 100, 1)
    ax.text(0, 0, f"{win_pct}%\nWIN RATE", ha="center", va="center",
            fontsize=13, fontweight="bold")
    ax.legend(wedges, ["WIN", "LOSE", "TIE"], loc="lower center", ncol=3,
              fontsize=8, bbox_to_anchor=(0.5, -0.06))
    plt.tight_layout()
    return fig


def chart_heatmap():
    if len(s.game_log) < 6:
        return None
    fig, ax = plt.subplots(figsize=(5, 4))
    grid = np.zeros((3, 3))
    for entry in s.game_log:
        pi = MOVES.index(entry["player_move"])
        ai = MOVES.index(entry["ai_move"])
        val = 1 if entry["result"] == "win" else (
            -1 if entry["result"] == "lose" else 0)
        grid[pi][ai] += val
    ax.imshow(grid, cmap="RdYlGn", vmin=-5, vmax=5)
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels([f"{EMOJIS[m]} AI" for m in MOVES])
    ax.set_yticklabels([f"You {EMOJIS[m]}" for m in MOVES])
    ax.set_title("Matchup Score (green=win)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{int(grid[i][j]):+d}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color="white")
    plt.tight_layout()
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("⚙ Settings")
    strategy_choice = st.selectbox(
        "AI Strategy",
        options=list(AI_STRATEGY_LABELS.keys()),
        format_func=lambda x: AI_STRATEGY_LABELS[x],
        index=list(AI_STRATEGY_LABELS.keys()).index(s.ai_strategy),
    )
    s.ai_strategy = strategy_choice

    strategy_info = {
        "frequency":  "Tracks overall move frequency. Effective after 5+ rounds.",
        "markov":     "Models transition probabilities. Strong against habitual patterns.",
        "adaptive":   "Ensemble of all models. Strongest overall performance.",
        "aggressive": "Focuses on recent 8 moves. Fast to adapt, can be baited.",
    }
    st.caption(strategy_info.get(s.ai_strategy, ""))

    s.show_debug = st.toggle("Show Debug Info", value=s.show_debug)

    if st.button("🔄 Reset Game", key="sidebar_reset"):
        reset_game()
        st.rerun()

    st.divider()
    st.caption("NEXUS RPS ENGINE · v2.0.0 · Built with Streamlit")

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN UI
# ═══════════════════════════════════════════════════════════════════════════════
st.title("⬡ NEXUS RPS ENGINE")
st.caption(
    f"Pattern Recognition AI · {AI_STRATEGY_LABELS.get(s.ai_strategy)} · {s.rounds} rounds played")
st.divider()

# ── Scoreboard ────────────────────────────────────────────────────────────────
sc = s.scores
tot = sum(sc.values()) or 1
col1, col2, col3, col4 = st.columns(4)
col1.metric("🟢 Your Wins", sc["player"], f"{round(sc['player']/tot*100,1)}%")
col2.metric("🔴 AI Wins",   sc["ai"],     f"{round(sc['ai']/tot*100,1)}%")
col3.metric("🟣 Ties",      sc["ties"],   f"{round(sc['ties']/tot*100,1)}%")
col4.metric("🔵 Rounds",    s.rounds,     "played")

win_rate = round(sc["player"] / tot * 100, 1)
st.progress(win_rate / 100, text=f"Win Rate: {win_rate}%")
st.divider()

# ── Achievement Toast ─────────────────────────────────────────────────────────
if s.new_achievement:
    icon, title, desc = s.new_achievement
    st.success(f"{icon} **Achievement Unlocked: {title}** — {desc}")
    s.new_achievement = None

# ── Play Area ─────────────────────────────────────────────────────────────────
col_play, col_info = st.columns([3, 2], gap="large")

with col_play:
    st.subheader("Make Your Move")
    st.caption(f"AI Engine: {AI_STRATEGY_LABELS.get(s.ai_strategy)} "
               + (f"· Last Confidence: {round(s.ai_confidence*100)}%" if s.rounds > 0 else ""))

    if s.ai_predicted and s.rounds > 2:
        st.caption(
            f"AI predicted your last move as: {EMOJIS[s.ai_predicted]} {s.ai_predicted.upper()}")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🪨\nROCK", key="btn_rock", use_container_width=True):
            play_round("rock")
            st.rerun()
    with c2:
        if st.button("📄\nPAPER", key="btn_paper", use_container_width=True):
            play_round("paper")
            st.rerun()
    with c3:
        if st.button("✂️\nSCISSORS", key="btn_scissors", use_container_width=True):
            play_round("scissors")
            st.rerun()

    st.write("")

    # Pattern warning
    if s.pattern_warning:
        st.warning(f"⚠️ Pattern Detected — {s.pattern_warning}")

    # Result display
    if s.last_round is None:
        st.info("🪨📄✂️  Awaiting your first move…")
    else:
        r = s.last_round
        result_icons = {"win": "🟢", "lose": "🔴", "tie": "🟣"}
        verdict_text = {"win": "YOU WIN 🎉",
                        "lose": "AI WINS 🤖", "tie": "IT'S A TIE 🤝"}
        st.write(f"**Round {r['round_no']}** — "
                 f"You: {EMOJIS[r['player_move']]} {r['player_move'].upper()}  vs  "
                 f"AI: {EMOJIS[r['ai_move']]} {r['ai_move'].upper()}")
        result_fn = {"win": st.success, "lose": st.error,
                     "tie": st.info}[r["result"]]
        result_fn(f"{result_icons[r['result']]}  **{verdict_text[r['result']]}**  "
                  f"(AI confidence: {round(r['confidence']*100)}%)")

    # Streak
    st.write("")
    streak = s.current_streak
    if streak > 0:
        st.success(f"🔥 {streak}-win streak!   Best: {s.best_win_streak}")
    elif streak < 0:
        st.error(
            f"❄️ {abs(streak)}-lose streak   Best win streak: {s.best_win_streak}")
    else:
        st.info(f"No active streak   Best win streak: {s.best_win_streak}")

with col_info:
    st.subheader("Move Distribution")
    for move in MOVES:
        count = s.move_freq[move]
        pct = count / (s.rounds or 1)
        st.write(f"{EMOJIS[move]} **{move.upper()}** — {count}")
        st.progress(pct)

    st.divider()
    st.subheader("Win / Loss Ratio")
    fig_donut = chart_result_donut()
    if fig_donut:
        st.pyplot(fig_donut, use_container_width=True)
    else:
        st.caption("Play a few rounds to see the chart.")

st.divider()

# ── Analytics Tabs ────────────────────────────────────────────────────────────
st.subheader("📊 Performance Analytics")
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Win Timeline", "🎯 Move Distribution", "🤖 AI Confidence", "🔥 Matchup Map"])

with tab1:
    fig = chart_win_timeline()
    if fig:
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Play at least 3 rounds to see the win timeline.")

with tab2:
    fig = chart_move_distribution()
    if fig:
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Play at least 1 round to see your move distribution.")

with tab3:
    fig = chart_ai_confidence()
    if fig:
        st.pyplot(fig, use_container_width=True)
        st.caption("Higher confidence = AI is more certain about your next move.")
    else:
        st.info("Play at least 3 rounds to see AI confidence over time.")

with tab4:
    fig = chart_heatmap()
    if fig:
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Play at least 6 rounds to see the matchup heatmap.")

st.divider()

# ── Game Log ──────────────────────────────────────────────────────────────────
st.subheader("📋 Round History")

if not s.game_log:
    st.caption("No rounds played yet.")
else:
    recent = list(reversed(s.game_log[-10:]))
    df = pd.DataFrame(recent)
    df = df.rename(columns={
        "round": "Round", "player_move": "Your Move", "ai_move": "AI Move",
        "result": "Result", "confidence": "AI Conf %", "ts": "Time"
    })
    df["Your Move"] = df["Your Move"].apply(
        lambda m: f"{EMOJIS[m]} {m.upper()}")
    df["AI Move"] = df["AI Move"].apply(lambda m: f"{EMOJIS[m]} {m.upper()}")
    df["Result"] = df["Result"].apply(
        lambda r: {"win": "✅ WIN", "lose": "❌ LOSE", "tie": "🟣 TIE"}[r])
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_data = pd.DataFrame(s.game_log).to_csv(index=False)
    col_e1, col_e2, col_e3 = st.columns([1, 2, 1])
    with col_e2:
        st.download_button(
            "⬇ Export Game Log (CSV)", data=csv_data,
            file_name=f"nexus_rps_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", use_container_width=True,
        )

st.divider()

# ── Achievements ──────────────────────────────────────────────────────────────
st.subheader("🏆 Achievements")
all_achv = [
    ("first_blood", "⚔️", "FIRST BLOOD",  "Played first round"),
    ("ten_rounds",  "🔟", "DECADE",        "10 rounds played"),
    ("streak_5",    "🔥", "ON FIRE",        "5-win streak"),
    ("streak_10",   "💥", "UNSTOPPABLE",   "10-win streak"),
    ("veteran",     "🎖️", "VETERAN",       "25 total wins"),
    ("endurance",   "🏃", "ENDURANCE",     "50 rounds played"),
    ("dominator",   "👑", "DOMINATOR",     ">70% win rate, 10+ rounds"),
]
achv_cols = st.columns(4)
for i, (key, icon, title, desc) in enumerate(all_achv):
    unlocked = key in s.achievements
    with achv_cols[i % 4]:
        if unlocked:
            st.success(f"{icon} **{title}**\n\n{desc} ✓")
        else:
            st.caption(f"{icon} {title} — {desc}")

st.divider()

# ── Tips ──────────────────────────────────────────────────────────────────────
st.subheader("💡 Strategy Tips")
tips = [
    ("🧠", "AI ADAPTS", "The engine builds a Markov model of your transitions. Every move trains it."),
    ("🎲", "STAY RANDOM", "True randomness beats pattern-based AI. Avoid repeated sequences."),
    ("📊", "WATCH THE BARS",
     "If one move dominates your frequency, the AI has likely adapted."),
    ("🔄", "SWITCH STRATEGY",
     "Change AI difficulty in the sidebar to test different engines."),
]
t1, t2 = st.columns(2)
for i, (icon, title, desc) in enumerate(tips):
    with (t1 if i % 2 == 0 else t2):
        st.info(f"{icon} **{title}** — {desc}")

st.divider()

# ── Debug Panel ───────────────────────────────────────────────────────────────
if s.show_debug and s.rounds > 0:
    st.subheader("🐛 Debug — Internal State")
    d1, d2 = st.columns(2)
    with d1:
        st.write("**Move Frequency**")
        st.json(s.move_freq)
        st.write("**Scores**")
        st.json(s.scores)
    with d2:
        st.write("**Markov Transition Matrix**")
        st.json(s.markov)
        st.write("**AI State**")
        st.json({"strategy": s.ai_strategy, "confidence": round(s.ai_confidence*100, 1),
                 "predicted": s.ai_predicted, "prev_move": s.prev_player_move})
    st.divider()

# ── Reset ─────────────────────────────────────────────────────────────────────
col_r1, col_r2, col_r3 = st.columns([1, 2, 1])
with col_r2:
    if st.button("↺ RESET GAME", key="bottom_reset", use_container_width=True):
        reset_game()
        st.rerun()

st.caption(f"NEXUS RPS ENGINE · v2.0.0 · {s.rounds} rounds played · "
           f"{len(s.achievements)}/7 achievements · Built with Streamlit")
