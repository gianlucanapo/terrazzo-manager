import streamlit as st
import sqlite3
import datetime
import time
import hashlib
import json
import random
from urllib.request import urlopen

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Terrazzo Booking & Casino", layout="centered")

# --- CUSTOM CSS (Modern UI) ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background-color: #f8fafc;
        background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
        background-size: 24px 24px;
        color: #0f172a;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container { max-width: 900px; padding-top: 3rem; padding-bottom: 5rem; }
    
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    h1, h2, h3 { font-weight: 700; color: #0f172a; }
    
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 12px rgba(37, 99, 235, 0.3); }
    
    input[type="text"], input[type="number"], input[type="password"], textarea {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #f1f5f9; }

    /* CARD GIOCO */
    .game-card {
        background-color: white;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 4px 8px;
        text-align: center;
        font-size: 1.1rem;
        font-weight: bold;
        display: inline-block;
        margin: 2px;
        min-width: 35px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .card-red { color: #dc2626; border-color: #fecaca; background-color: #fff1f2; }
    .card-black { color: #0f172a; border-color: #cbd5e1; }
    
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        text-transform: uppercase;
    }
    .status-playing { background-color: #dbeafe; color: #1e40af; }
    .status-stand { background-color: #f3f4f6; color: #4b5563; }
    .status-bust { background-color: #fee2e2; color: #991b1b; }
    .status-win { background-color: #d1fae5; color: #065f46; }
    .status-bj { background-color: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }
    .status-insurance { background-color: #e0e7ff; color: #4338ca; border: 1px solid #c7d2fe; }
    
    .active-hand {
        border: 2px solid #2563eb !important;
        background-color: #eff6ff !important;
        transform: scale(1.02);
    }
    </style>
    """, unsafe_allow_html=True)

# DATABASE
DB_NAME = 'terrazzo_vito.db' 
LINK_REVOLUT = "https://revolut.me/gianlunapolano"
VITO_ADDRESS = "Via Arenella, 95, 80128 Napoli NA"
VITO_MAP_URL = "https://www.google.com/maps/search/?api=1&query=Via+Arenella+95+Napoli"

# --- UTILITÀ SICUREZZA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

# --- UTILITÀ METEO ---
def get_weather_napoli_live():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=40.8518&longitude=14.2681&current_weather=true"
        response = urlopen(url)
        data = json.loads(response.read())
        t = data['current_weather']['temperature']
        w = data['current_weather']['windspeed']
        c = data['current_weather']['weathercode']
        icon = "☀️" if c <= 3 else "🌧️"
        return f"{icon} {t}°C", f"Vento: {w} km/h"
    except: return "🌡️ N/D", "-"

def get_forecast_for_date(date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude=40.8518&longitude=14.2681&daily=weathercode,temperature_2m_max&timezone=auto&start_date={date_str}&end_date={date_str}"
        response = urlopen(url)
        data = json.loads(response.read())
        if 'daily' in data and 'weathercode' in data['daily']:
            wcode = data['daily']['weathercode'][0]
            temp_max = data['daily']['temperature_2m_max'][0]
            return (wcode >= 51), temp_max
    except: return False, None

# --- DATABASE ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def ensure_column(conn, table, col, coldef):
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
    except: pass

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabelle Base
    c.execute('''CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, tema TEXT, creator TEXT, description TEXT, is_confirmed INTEGER DEFAULT 1, UNIQUE(data, ora))''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, nome_amico TEXT, note TEXT, plus_one INTEGER DEFAULT 0, nome_plus_one TEXT, tieni_status INTEGER DEFAULT 0, FOREIGN KEY(slot_id) REFERENCES slots(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS donazioni (id INTEGER PRIMARY KEY AUTOINCREMENT, donatore TEXT, importo REAL, username TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS goal (id INTEGER PRIMARY KEY, description TEXT, target REAL, current REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bringing (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, username TEXT, item TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS waitlist (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, username TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS event_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, username TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # --- TABELLE BLACKJACK ---
    c.execute('''CREATE TABLE IF NOT EXISTS bj_game (
        id INTEGER PRIMARY KEY,
        status TEXT,
        dealer_hand TEXT,
        dealer_initial_hand TEXT,
        current_player_index INTEGER,
        current_hand_index INTEGER,
        deck TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bj_players (
        username TEXT PRIMARY KEY,
        status TEXT,
        bankroll INTEGER DEFAULT 2000,
        bet_main INTEGER DEFAULT 0,
        bet_pair INTEGER DEFAULT 0,
        bet_21p3 INTEGER DEFAULT 0,
        insurance_bet INTEGER DEFAULT 0,
        insurance_taken INTEGER DEFAULT 0,
        side_result TEXT DEFAULT '',
        main_result TEXT DEFAULT ''
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bj_hands (
        username TEXT,
        hand_index INTEGER,
        hand TEXT,
        score INTEGER,
        status TEXT,
        bet INTEGER,
        doubled INTEGER DEFAULT 0,
        is_split_hand INTEGER DEFAULT 0,
        PRIMARY KEY (username, hand_index)
    )''')

    # Migrazioni Sicure
    ensure_column(conn, "bj_game", "dealer_initial_hand", "TEXT DEFAULT '[]'")
    ensure_column(conn, "bj_game", "current_hand_index", "INTEGER DEFAULT 0")
    ensure_column(conn, "bj_players", "insurance_bet", "INTEGER DEFAULT 0")
    ensure_column(conn, "bj_players", "insurance_taken", "INTEGER DEFAULT 0")
    ensure_column(conn, "bj_hands", "is_split_hand", "INTEGER DEFAULT 0")
    
    if c.execute("SELECT count(*) FROM bj_game").fetchone()[0] == 0:
        c.execute("INSERT INTO bj_game (id, status, dealer_hand, dealer_initial_hand, current_player_index, current_hand_index, deck) VALUES (1,'WAITING','[]','[]',0,0,'[]')")
    
    if c.execute("SELECT count(*) FROM goal").fetchone()[0] == 0:
        c.execute("INSERT INTO goal (id, description, target, current) VALUES (1, 'Fondo Serate', 100.0, 0.0)")

    conn.commit()
    conn.close()

init_db()

# --- LOGICA BLACKJACK & COSTANTI ---
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUE_21P3 = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
PAIR_PAYOUT = {"mixed": 6, "colored": 12, "perfect": 25}
P21P3_PAYOUT = {"straight_flush": 40, "three_kind": 30, "straight": 10, "flush": 5, "pair": 5}

def create_deck():
    deck = [{'rank': r, 'suit': s} for s in SUITS for r in RANKS] * 6 # 6 mazzi
    random.shuffle(deck)
    return json.dumps(deck)

# Helper per gestire refill mazzo (Fix #2)
def pop_card(deck):
    if len(deck) == 0:
        deck[:] = json.loads(create_deck()) # Replace content
    return deck.pop()

def calculate_score(hand):
    score = 0
    aces = 0
    for card in hand:
        if card['rank'] in ['J', 'Q', 'K']: score += 10
        elif card['rank'] == 'A':
            aces += 1
            score += 11
        else: score += int(card['rank'])
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def is_blackjack(hand):
    return len(hand) == 2 and calculate_score(hand) == 21

def is_pair_for_split(hand):
    return len(hand) == 2 and hand[0]['rank'] == hand[1]['rank']

def dealer_upcard(dealer_hand):
    return dealer_hand[0] if dealer_hand else None

def is_ace(card):
    return card and card.get('rank') == 'A'

def suit_color_group(suit):
    return "red" if suit in ['♥', '♦'] else "black"

# --- SIDE BETS LOGIC ---
def settle_pair(player_hand):
    if len(player_hand) < 2: return 0, ""
    c1, c2 = player_hand[0], player_hand[1]
    if c1['rank'] != c2['rank']: return 0, ""
    if c1['suit'] == c2['suit']: return PAIR_PAYOUT["perfect"], "Perfect Pair (25x)"
    if suit_color_group(c1['suit']) == suit_color_group(c2['suit']): return PAIR_PAYOUT["colored"], "Color Pair (12x)"
    return PAIR_PAYOUT["mixed"], "Mixed Pair (6x)"

def settle_21p3(player_hand, dealer_upcard):
    if len(player_hand) < 2 or dealer_upcard is None: return 0, ""
    cards = [player_hand[0], player_hand[1], dealer_upcard]
    ranks = [c['rank'] for c in cards]; suits = [c['suit'] for c in cards]
    vals = sorted([RANK_VALUE_21P3[r] for r in ranks])
    
    flush = len(set(suits)) == 1
    counts = {r: ranks.count(r) for r in set(ranks)}
    three_kind = 3 in counts.values()
    pair = 2 in counts.values()
    
    # Straight logic (A-2-3 check included)
    straight = (vals == [2, 3, 14]) or (vals[0]+1 == vals[1] and vals[1]+1 == vals[2])
    
    if straight and flush: return P21P3_PAYOUT["straight_flush"], "Straight Flush (40x)"
    if three_kind: return P21P3_PAYOUT["three_kind"], "Three of a Kind (30x)"
    if straight: return P21P3_PAYOUT["straight"], "Straight (10x)"
    if flush: return P21P3_PAYOUT["flush"], "Flush (5x)"
    if pair: return P21P3_PAYOUT["pair"], "One Pair (5x)" # Attenzione: regole variano, qui diamo 5x
    return 0, ""

# --- AZIONI GIOCO ---
def can_take_insurance_strict(conn, username):
    """
    Regola rigida: Insurance solo se status è INSURANCE
    """
    status = conn.execute("SELECT status FROM bj_game WHERE id=1").fetchone()[0]
    if status != "INSURANCE": return False
    
    # Check mani giocatore
    hands = conn.execute("SELECT hand FROM bj_hands WHERE username=?", (username,)).fetchall()
    if len(hands) != 1: return False # Ha splittato o errore
    
    try:
        hand0 = json.loads(hands[0][0] or "[]")
    except:
        return False

    if len(hand0) != 2: return False # Ha già hittato
    
    taken = conn.execute("SELECT insurance_taken FROM bj_players WHERE username=?", (username,)).fetchone()[0]
    if taken: return False
    
    return True

def join_blackjack(username):
    conn = get_connection()
    status = conn.execute("SELECT status FROM bj_game WHERE id=1").fetchone()[0]
    if status in ['PLAYING', 'INSURANCE']:
        conn.close(); return False, "Gioco in corso!"
    try:
        conn.execute("INSERT INTO bj_players (username, status, bankroll, bet_main, bet_pair, bet_21p3, insurance_bet, insurance_taken, side_result, main_result) VALUES (?, 'READY', 2000, 0, 0, 0, 0, 0, '', '')", (username,))
        # Crea mano vuota placeholder
        conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 0, '[]', 0, 'READY', 0, 0, 0)", (username,))
        conn.commit(); conn.close()
        return True, "Seduto!"
    except:
        conn.close(); return True, "Già seduto."

def leave_blackjack(username):
    conn = get_connection()
    conn.execute("DELETE FROM bj_hands WHERE username=?", (username,))
    conn.execute("DELETE FROM bj_players WHERE username=?", (username,))
    cnt = conn.execute("SELECT count(*) FROM bj_players").fetchone()[0]
    if cnt == 0:
        conn.execute("UPDATE bj_game SET status='WAITING', dealer_hand='[]', dealer_initial_hand='[]', current_player_index=0, current_hand_index=0, deck='[]' WHERE id=1")
    conn.commit(); conn.close()

def start_game():
    conn = get_connection()
    deck = json.loads(create_deck())
    players = conn.execute("SELECT username, bankroll, bet_main, bet_pair, bet_21p3 FROM bj_players").fetchall()
    
    if not players: conn.close(); return False, "Nessun giocatore"

    # VALIDAZIONE SCOMMESSE LATO SERVER
    valid_players = [] # (Clean up fix)
    bad_players = []
    for u, br, bm, bp, b213 in players:
        bm, bp, b213, br = int(bm or 0), int(bp or 0), int(b213 or 0), int(br or 0)
        if bm > 0 and (bm + bp + b213) <= br:
            valid_players.append(u)
        else:
            bad_players.append(u)
    
    if len(bad_players) > 0:
        conn.close()
        return False, f"Puntate non valide per: {', '.join(bad_players)}"

    # Deal dealer
    dealer_hand = [pop_card(deck), pop_card(deck)]
    d_initial = dealer_hand[:]
    up = dealer_hand[0]
    
    conn.execute("DELETE FROM bj_hands") # Pulisce mani precedenti

    for u, br, bm, bp, b213 in players:
        bm, bp, b213, br = int(bm or 0), int(bp or 0), int(b213 or 0), int(br or 0)
        p_hand = [pop_card(deck), pop_card(deck)]
        p_score = calculate_score(p_hand)
        total_bet = bm + bp + b213
        br -= total_bet
        
        # Side Bets
        side_msgs = []
        if bp > 0:
            mult, lbl = settle_pair(p_hand)
            if mult > 0: br += int(bp * (mult + 1)); side_msgs.append(lbl)
        if b213 > 0:
            mult, lbl = settle_21p3(p_hand, up)
            if mult > 0: br += int(b213 * (mult + 1)); side_msgs.append(lbl)
            
        p_status = "PLAYING"
        if p_score == 21: p_status = "STAND" # BJ naturale gestito alla fine

        conn.execute("UPDATE bj_players SET status='PLAYING', bankroll=?, side_result=?, main_result='', insurance_bet=0, insurance_taken=0 WHERE username=?", (br, " | ".join(side_msgs), u))
        conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 0, ?, ?, ?, ?, 0, 0)", (u, json.dumps(p_hand), p_score, p_status, bm))

    # DEALER PEEK (Bug Fix #1: Immediate peek ONLY on 10-value, wait on Ace for insurance)
    dealer_has_blackjack = is_blackjack(d_initial)
    up_rank = up['rank']
    up_is_ten = up_rank in ['10','J','Q','K']
    is_ace_up = is_ace(up)

    next_status = 'PLAYING'
    if is_ace_up:
        next_status = 'INSURANCE'

    conn.execute("UPDATE bj_game SET status=?, deck=?, dealer_hand=?, dealer_initial_hand=?, current_player_index=0, current_hand_index=0 WHERE id=1", (next_status, json.dumps(deck), json.dumps(dealer_hand), json.dumps(d_initial)))
    conn.commit()

    if dealer_has_blackjack and up_is_ten:
        conn.close()
        end_round() # Chiude subito
        return True, "Banco Blackjack! Partita terminata."
    
    conn.close()
    
    # Se non c'è insurance, controlla se qualcuno ha BJ o passa turno
    if next_status == 'PLAYING':
        next_turn_logic()
        
    return True, "Partita iniziata"

def close_insurance_phase(username):
    conn = get_connection()
    
    seated = conn.execute("SELECT 1 FROM bj_players WHERE username=?", (username,)).fetchone()
    if not seated:
        conn.close()
        return False, "Non sei seduto al tavolo."

    d_initial_json = conn.execute("SELECT dealer_initial_hand FROM bj_game WHERE id=1").fetchone()[0]
    d_initial = json.loads(d_initial_json)
    
    if is_blackjack(d_initial):
        conn.close()
        end_round()
        return True, "Banco ha Blackjack!"
    else:
        conn.execute("UPDATE bj_game SET status='PLAYING' WHERE id=1")
        conn.commit()
        conn.close()
        next_turn()
        return False, "Niente Blackjack, si gioca!"

def next_turn_logic():
    next_turn()

def next_turn():
    conn = get_connection()
    players = conn.execute("SELECT username FROM bj_players ORDER BY rowid").fetchall()
    if not players: conn.close(); return

    curr_p_idx, curr_h_idx = conn.execute("SELECT current_player_index, current_hand_index FROM bj_game WHERE id=1").fetchone()
    
    # 1. Prova mani successive dello stesso giocatore o mani attuali se ancora PLAYING
    # Scansiona dal giocatore corrente in avanti
    for i in range(curr_p_idx, len(players)):
        user = players[i][0]
        start_h = curr_h_idx if i == curr_p_idx else 0
        hands = conn.execute("SELECT hand_index FROM bj_hands WHERE username=? AND status='PLAYING' AND hand_index >= ? ORDER BY hand_index", (user, start_h)).fetchone()
        if hands:
            conn.execute("UPDATE bj_game SET current_player_index=?, current_hand_index=? WHERE id=1", (i, hands[0]))
            conn.commit(); conn.close(); return

    # 2. WRAP-AROUND: Se siamo arrivati in fondo, ricomincia dall'inizio fino al giocatore corrente (esclusa la mano attuale che abbiamo già controllato)
    # Utile se l'ordine si è sfasato o se ci sono mani rimaste indietro
    for i in range(0, curr_p_idx + 1):
        user = players[i][0]
        # Se è lo stesso player di partenza, ci fermiamo a curr_h_idx - 1 per non ciclare infinito
        end_h_limit = 999 if i != curr_p_idx else curr_h_idx
        hands = conn.execute("SELECT hand_index FROM bj_hands WHERE username=? AND status='PLAYING' AND hand_index < ? ORDER BY hand_index", (user, end_h_limit)).fetchone()
        if hands:
            conn.execute("UPDATE bj_game SET current_player_index=?, current_hand_index=? WHERE id=1", (i, hands[0]))
            conn.commit(); conn.close(); return
            
    # Se nessuno ha mani PLAYING -> Dealer Turn
    conn.commit(); conn.close()
    end_round()

def get_current_turn(conn):
    p_idx, h_idx = conn.execute("SELECT current_player_index, current_hand_index FROM bj_game WHERE id=1").fetchone()
    players = conn.execute("SELECT username FROM bj_players ORDER BY rowid").fetchall()
    if not players or p_idx >= len(players): return None, None, None
    return players[p_idx][0], p_idx, h_idx

def player_hit(username):
    conn = get_connection()
    turn_user, _, h_idx = get_current_turn(conn)
    if turn_user != username: conn.close(); return
    
    deck = json.loads(conn.execute("SELECT deck FROM bj_game WHERE id=1").fetchone()[0])
    row = conn.execute("SELECT hand FROM bj_hands WHERE username=? AND hand_index=?", (username, h_idx)).fetchone()
    hand = json.loads(row[0])
    
    hand.append(pop_card(deck))
    score = calculate_score(hand)
    status = "PLAYING"
    if score > 21: status = "BUST"
    elif score == 21: status = "STAND"
    
    conn.execute("UPDATE bj_hands SET hand=?, score=?, status=? WHERE username=? AND hand_index=?", (json.dumps(hand), score, status, username, h_idx))
    conn.execute("UPDATE bj_game SET deck=? WHERE id=1", (json.dumps(deck),))
    conn.commit(); conn.close()
    if status != "PLAYING": next_turn()
    return status

def player_stand(username):
    conn = get_connection()
    turn_user, _, h_idx = get_current_turn(conn)
    if turn_user != username: conn.close(); return
    conn.execute("UPDATE bj_hands SET status='STAND' WHERE username=? AND hand_index=?", (username, h_idx))
    conn.commit(); conn.close()
    next_turn()

def player_double(username):
    conn = get_connection()
    turn_user, _, h_idx = get_current_turn(conn)
    if turn_user != username: conn.close(); return "NOT_YOUR_TURN"

    hand_row = conn.execute("SELECT hand, bet, doubled, status FROM bj_hands WHERE username=? AND hand_index=?", (username, h_idx)).fetchone()
    hand = json.loads(hand_row[0]); bet = int(hand_row[1]); doubled = int(hand_row[2]); status = hand_row[3]
    
    if len(hand) != 2 or doubled == 1 or status != "PLAYING":
        conn.close(); return "NOT_ALLOWED"
    
    bankroll = int(conn.execute("SELECT bankroll FROM bj_players WHERE username=?", (username,)).fetchone()[0])
    if bankroll < bet: conn.close(); return "NO_MONEY"
    
    deck = json.loads(conn.execute("SELECT deck FROM bj_game WHERE id=1").fetchone()[0])
    bankroll -= bet
    hand.append(pop_card(deck))
    score = calculate_score(hand)
    
    # Dopo double ricevi una sola carta e ti fermi
    status = "STAND"
    if score > 21: status = "BUST"
    
    conn.execute("UPDATE bj_players SET bankroll=? WHERE username=?", (bankroll, username))
    conn.execute("UPDATE bj_hands SET hand=?, score=?, status=?, bet=?, doubled=1 WHERE username=? AND hand_index=?", (json.dumps(hand), score, status, bet*2, username, h_idx))
    conn.execute("UPDATE bj_game SET deck=? WHERE id=1", (json.dumps(deck),))
    conn.commit(); conn.close()
    next_turn()
    return "OK"

def player_split(username):
    conn = get_connection()
    turn_user, _, h_idx = get_current_turn(conn)
    
    if turn_user != username or h_idx != 0: conn.close(); return "NOT_ALLOWED"
    
    cnt = conn.execute("SELECT count(*) FROM bj_hands WHERE username=?", (username,)).fetchone()[0]
    if cnt > 1: conn.close(); return "MAX_SPLIT"
    
    hand_row = conn.execute("SELECT hand, bet FROM bj_hands WHERE username=? AND hand_index=?", (username, h_idx)).fetchone()
    hand = json.loads(hand_row[0]); bet = int(hand_row[1])
    
    if len(hand) != 2 or not is_pair_for_split(hand):
        conn.close(); return "NOT_PAIR"
    
    bankroll = int(conn.execute("SELECT bankroll FROM bj_players WHERE username=?", (username,)).fetchone()[0])
    if bankroll < bet: conn.close(); return "NO_MONEY"
    
    deck = json.loads(conn.execute("SELECT deck FROM bj_game WHERE id=1").fetchone()[0])
    
    # Split
    c1 = hand[0]; c2 = hand[1]
    h1 = [c1, pop_card(deck)]
    h2 = [c2, pop_card(deck)]
    
    # SPLIT ACES RULE: Se sono Assi, una carta e stop
    split_aces = (c1['rank'] == 'A' and c2['rank'] == 'A')
    status_after = "STAND" if split_aces else "PLAYING"
    
    bankroll -= bet
    conn.execute("UPDATE bj_players SET bankroll=? WHERE username=?", (bankroll, username))
    
    # Update mano 0, crea mano 1 -> SETTIAMO is_split_hand=1 per entrambe
    conn.execute("UPDATE bj_hands SET hand=?, score=?, status=?, is_split_hand=1 WHERE username=? AND hand_index=0", (json.dumps(h1), calculate_score(h1), status_after, username))
    conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 1, ?, ?, ?, ?, 0, 1)", (username, json.dumps(h2), calculate_score(h2), status_after, bet))
    conn.execute("UPDATE bj_game SET deck=? WHERE id=1", (json.dumps(deck),))
    
    conn.commit(); conn.close()
    
    if split_aces:
        next_turn()
        
    return "OK"

def player_insurance(username, amount):
    conn = get_connection()
    if not can_take_insurance_strict(conn, username): 
        conn.close(); return "NOT_ALLOWED"
    
    bankroll = int(conn.execute("SELECT bankroll FROM bj_players WHERE username=?", (username,)).fetchone()[0])
    if bankroll < amount: conn.close(); return "NO_MONEY"
    
    bankroll -= amount
    conn.execute("UPDATE bj_players SET bankroll=?, insurance_bet=?, insurance_taken=1 WHERE username=?", (bankroll, amount, username))
    conn.commit(); conn.close()
    return "OK"

def end_round():
    conn = get_connection()
    game = conn.execute("SELECT deck, dealer_hand, dealer_initial_hand FROM bj_game WHERE id=1").fetchone()
    deck = json.loads(game[0])
    d_hand = json.loads(game[1])
    d_initial = json.loads(game[2])
    
    # Dealer gioca
    d_score = calculate_score(d_hand)
    while d_score < 17:
        d_hand.append(pop_card(deck))
        d_score = calculate_score(d_hand)
    
    dealer_bj = is_blackjack(d_initial)
    
    # Pagamenti
    players = conn.execute("SELECT username, bankroll, insurance_bet FROM bj_players").fetchall()
    for u, br, ins in players:
        br = int(br); ins = int(ins)
        if ins > 0 and dealer_bj: br += ins * 3 # Paga 2:1 + restituisce
        
        # Check hands
        hands = conn.execute("SELECT hand, score, status, bet, is_split_hand FROM bj_hands WHERE username=?", (u,)).fetchall()
        res_str = []
        for h_json, sc, stt, bet, is_split in hands:
            bet = int(bet)
            hand = json.loads(h_json)
            p_bj = is_blackjack(hand)
            
            outcome = "Perso"
            if stt == 'BUST': outcome = "Sballato"
            else:
                if dealer_bj:
                    if p_bj: 
                        if not is_split: # Real BJ vs BJ => Push
                            outcome = "Push"; br += bet
                        else: # Split 21 vs BJ => Perso
                            outcome = "Banco BJ"
                    else: outcome = "Banco BJ"
                elif p_bj:
                    if not is_split: # Natural BJ
                        outcome = "Blackjack!"; br += int(bet * 2.5) # 3:2 payout
                    else: # Split 21 => Paga 1:1
                        outcome = "21 (Split)"; br += bet * 2
                elif d_score > 21:
                    outcome = "Vinto"; br += bet * 2
                elif sc > d_score:
                    outcome = "Vinto"; br += bet * 2
                elif sc == d_score:
                    outcome = "Push"; br += bet
            
            res_str.append(outcome)
            
        conn.execute("UPDATE bj_players SET bankroll=?, main_result=? WHERE username=?", (br, " | ".join(res_str), u))
    
    conn.execute("UPDATE bj_game SET dealer_hand=?, status='FINISHED' WHERE id=1", (json.dumps(d_hand),))
    conn.commit(); conn.close()

def reset_round():
    conn = get_connection()
    conn.execute("UPDATE bj_game SET status='WAITING', dealer_hand='[]', dealer_initial_hand='[]', current_player_index=0, current_hand_index=0 WHERE id=1")
    conn.execute("UPDATE bj_players SET status='READY', insurance_bet=0, insurance_taken=0, side_result='', main_result=''")
    conn.execute("DELETE FROM bj_hands")
    # Ricrea mani vuote per i seduti
    users = conn.execute("SELECT username FROM bj_players").fetchall()
    for u in users:
        conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 0, '[]', 0, 'READY', 0, 0, 0)", (u[0],))
    conn.commit(); conn.close()

# --- SEZIONE BLACKJACK ---
def blackjack_section():
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.title("🎰 Terrazzo Casino: Blackjack")
    
    username = st.session_state.username
    conn = get_connection()
    # REFRESH DATA HERE for UI Consistency (Fix #2)
    game_state = conn.execute("SELECT status, dealer_hand, current_player_index FROM bj_game WHERE id=1").fetchone()
    players_data = conn.execute("SELECT username, bankroll, bet_main, bet_pair, bet_21p3, side_result, main_result, insurance_taken FROM bj_players ORDER BY rowid").fetchall()
    
    status, d_hand_json, curr_idx = game_state
    d_hand = json.loads(d_hand_json)
    
    is_seated = any(p[0] == username for p in players_data)
    conn.close()

    # --- LOBBY ---
    if status == 'WAITING':
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 🛋️ Al tavolo:")
            if not players_data: st.write("Tavolo vuoto.")
            for p in players_data:
                st.write(f"👤 {p[0]} (🪙 {p[1]})") # SIMBOLO 🪙
        with c2:
            if not is_seated:
                if st.button("Siediti"): join_blackjack(username); st.rerun()
            else:
                if st.button("Alzati"): leave_blackjack(username); st.rerun()
                
        if is_seated:
            st.divider()
            st.write("### 💵 Piazza le puntate")
            conn = get_connection()
            me = conn.execute("SELECT bankroll, bet_main, bet_pair, bet_21p3 FROM bj_players WHERE username=?", (username,)).fetchone()
            conn.close()
            
            c_m, c_p, c_s = st.columns(3)
            bm = c_m.number_input("Main", value=int(me[1]), step=10, min_value=0)
            bp = c_p.number_input("Pair", value=int(me[2]), step=5, min_value=0)
            bs = c_s.number_input("21+3", value=int(me[3]), step=5, min_value=0)
            
            if st.button("Salva Puntate"):
                conn = get_connection()
                conn.execute("UPDATE bj_players SET bet_main=?, bet_pair=?, bet_21p3=? WHERE username=?", (bm, bp, bs, username))
                conn.commit(); conn.close()
                st.success("Puntata salvata!")
                time.sleep(0.5); st.rerun()
                
            if st.button("🚀 START GAME"):
                success, msg = start_game() # FEEDBACK ERRORE
                if success:
                    st.rerun()
                else:
                    st.error(msg)
        
        time.sleep(2); st.rerun()

    # --- GIOCO ---
    else:
        # DEALER
        st.write("### 🎩 Dealer")
        cols = st.columns(6)
        d_score = "?"
        if status == 'FINISHED':
            d_score = calculate_score(d_hand)
        
        for i, card in enumerate(d_hand):
            # Se stiamo giocando o in insurance, nascondi la seconda carta
            if (status == 'PLAYING' or status == 'INSURANCE') and i == 1:
                cols[i].markdown("<div class='game-card card-black'>🂠</div>", unsafe_allow_html=True)
            else:
                color = "card-red" if card['suit'] in ['♥', '♦'] else "card-black"
                cols[i].markdown(f"<div class='game-card {color}'>{card['rank']}{card['suit']}</div>", unsafe_allow_html=True)
        st.caption(f"Punti: {d_score}")
        
        # STATUS BAR EXTRA
        if status == 'INSURANCE':
            st.markdown("<span class='status-badge status-insurance'>INSURANCE</span>", unsafe_allow_html=True)
            st.warning("⚠️ Il banco ha un Asso! Insurance aperta.")
        
        st.divider()
        
        # GIOCATORI
        conn = get_connection()
        
        # Use get_current_turn only in PLAYING to avoid issues in INSURANCE phase
        curr_p_name = curr_p_idx = curr_h_idx = None
        if status == 'PLAYING':
            curr_p_name, curr_p_idx, curr_h_idx = get_current_turn(conn)
        
        # Mostra tutti i giocatori
        p_cols = st.columns(len(players_data) if len(players_data) > 0 else 1)
        
        for i, p_data in enumerate(players_data):
            p_name = p_data[0]
            # Recupera mani
            hands = conn.execute("SELECT hand_index, hand, score, status, bet FROM bj_hands WHERE username=? ORDER BY hand_index", (p_name,)).fetchall()
            
            with p_cols[i]:
                st.write(f"**{p_name}**")
                st.caption(f"🪙 {p_data[1]}") # SIMBOLO 🪙
                if p_data[5]: st.info(f"Side: {p_data[5]}") # Side result
                if status == 'FINISHED' and p_data[6]: st.success(p_data[6]) # Main result
                
                # Visualizza insurance presa
                if p_data[7]: st.caption("🛡️ Insured")

                for h in hands:
                    idx, h_json, sc, stt, bt = h
                    hand_cards = json.loads(h_json)
                    
                    # Style active hand
                    is_active = (p_name == curr_p_name and idx == curr_h_idx and status == 'PLAYING')
                    bg = "background-color: #eff6ff; border: 2px solid #3b82f6;" if is_active else ""
                    
                    st.markdown(f"<div style='padding:5px; border-radius:8px; {bg}'>", unsafe_allow_html=True)
                    h_html = ""
                    for c in hand_cards:
                        clr = "card-red" if c['suit'] in ['♥', '♦'] else "card-black"
                        h_html += f"<span class='game-card {clr}'>{c['rank']}{c['suit']}</span>"
                    st.markdown(h_html, unsafe_allow_html=True)
                    st.caption(f"Bet: {bt} | Punti: {sc}")
                    if stt != 'PLAYING': st.caption(f"*{stt}*")
                    st.markdown("</div>", unsafe_allow_html=True)

        conn.close()
        
        # --- FASE INSURANCE ---
        if status == 'INSURANCE':
            st.write("---")
            st.markdown("### 🛡️ Fase Insurance")
            
            # Bottoni Insurance per chi è seduto
            if is_seated:
                conn = get_connection()
                if can_take_insurance_strict(conn, username):
                     bet0 = int(conn.execute("SELECT bet FROM bj_hands WHERE username=? AND hand_index=0", (username,)).fetchone()[0])
                     ins_amt = bet0 // 2
                     if st.button(f"Compra Insurance ({ins_amt})", key="buy_ins"):
                         res = player_insurance(username, ins_amt)
                         if res == "OK": st.success("Presa!"); st.rerun()
                         else: st.error(res)
                else:
                    # Se l'ha già presa o non può
                    taken = conn.execute("SELECT insurance_taken FROM bj_players WHERE username=?", (username,)).fetchone()[0]
                    if taken: st.info("Hai già preso l'Insurance.")
                conn.close()

            # Bottone per chiudere la fase (visibile a tutti i seduti)
            if is_seated:
                if st.button("➡️ Continua / Rivela"):
                    end, msg = close_insurance_phase(username)
                    if end: st.error(msg)
                    else: st.success(msg)
                    st.rerun()

        # --- PULSANTIERA (SOLO TUO TURNO E GIOCO ATTIVO) ---
        elif status == 'PLAYING' and username == curr_p_name:
            st.write("---")
            st.markdown("### 🔥 Tocca a te!")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("HIT 🃏"):
                player_hit(username)
                st.rerun()
            if c2.button("STAND ✋"):
                player_stand(username)
                st.rerun()
            if c3.button("DOUBLE 2️⃣"):
                res = player_double(username)
                if res != "OK": st.error(res)
                else: st.rerun()
            if c4.button("SPLIT ✂️"):
                res = player_split(username)
                if res != "OK": st.error(res)
                else: st.rerun()

        elif status == 'FINISHED':
            st.write("---")
            if st.button("Rigioca 🔄"):
                reset_round()
                st.rerun()
        else:
            time.sleep(2); st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)
