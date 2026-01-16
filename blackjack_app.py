import streamlit as st
import sqlite3
import json
import random
import time
import hashlib

# --- CONFIGURAZIONE E COSTANTI ---
DB_NAME = 'terrazzo_vito.db' 

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUE_21P3 = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2}
PAIR_PAYOUT = {"mixed": 6, "colored": 12, "perfect": 25}
P21P3_PAYOUT = {"straight_flush": 40, "three_kind": 30, "straight": 10, "flush": 5, "pair": 5}

# --- DATABASE HELPERS ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def ensure_column(conn, table, col, coldef):
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
    except: pass

def init_blackjack_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabelle Blackjack
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

    # Migrazioni
    ensure_column(conn, "bj_game", "dealer_initial_hand", "TEXT DEFAULT '[]'")
    ensure_column(conn, "bj_game", "current_hand_index", "INTEGER DEFAULT 0")
    ensure_column(conn, "bj_players", "insurance_bet", "INTEGER DEFAULT 0")
    ensure_column(conn, "bj_players", "insurance_taken", "INTEGER DEFAULT 0")
    ensure_column(conn, "bj_hands", "is_split_hand", "INTEGER DEFAULT 0")
    
    if c.execute("SELECT count(*) FROM bj_game").fetchone()[0] == 0:
        c.execute("INSERT INTO bj_game (id, status, dealer_hand, dealer_initial_hand, current_player_index, current_hand_index, deck) VALUES (1,'WAITING','[]','[]',0,0,'[]')")
    
    conn.commit()
    conn.close()

# --- LOGICA DI GIOCO ---
def create_deck():
    deck = [{'rank': r, 'suit': s} for s in SUITS for r in RANKS] * 6 
    random.shuffle(deck)
    return json.dumps(deck)

def pop_card(deck):
    if len(deck) == 0:
        deck[:] = json.loads(create_deck())
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
    straight = (vals == [2, 3, 14]) or (vals[0]+1 == vals[1] and vals[1]+1 == vals[2])
    
    if straight and flush: return P21P3_PAYOUT["straight_flush"], "Straight Flush (40x)"
    if three_kind: return P21P3_PAYOUT["three_kind"], "Three of a Kind (30x)"
    if straight: return P21P3_PAYOUT["straight"], "Straight (10x)"
    if flush: return P21P3_PAYOUT["flush"], "Flush (5x)"
    if pair: return P21P3_PAYOUT["pair"], "One Pair (5x)"
    return 0, ""

def can_take_insurance_strict(conn, username):
    status = conn.execute("SELECT status FROM bj_game WHERE id=1").fetchone()[0]
    if status != "INSURANCE": return False
    hands = conn.execute("SELECT hand FROM bj_hands WHERE username=?", (username,)).fetchall()
    if len(hands) != 1: return False
    try: hand0 = json.loads(hands[0][0] or "[]")
    except: return False
    if len(hand0) != 2: return False
    taken = conn.execute("SELECT insurance_taken FROM bj_players WHERE username=?", (username,)).fetchone()[0]
    if taken: return False
    return True

# --- AZIONI DEL GIOCO ---
def join_blackjack(username):
    conn = get_connection()
    status = conn.execute("SELECT status FROM bj_game WHERE id=1").fetchone()[0]
    if status in ['PLAYING', 'INSURANCE']:
        conn.close(); return False, "Gioco in corso!"
    try:
        conn.execute("INSERT INTO bj_players (username, status, bankroll, bet_main, bet_pair, bet_21p3, insurance_bet, insurance_taken, side_result, main_result) VALUES (?, 'READY', 2000, 0, 0, 0, 0, 0, '', '')", (username,))
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

    valid_players = []
    bad_players = []
    for u, br, bm, bp, b213 in players:
        bm, bp, b213, br = int(bm or 0), int(bp or 0), int(b213 or 0), int(br or 0)
        if bm > 0 and (bm + bp + b213) <= br: valid_players.append(u)
        else: bad_players.append(u)
    
    if len(bad_players) > 0:
        conn.close(); return False, f"Puntate non valide per: {', '.join(bad_players)}"

    dealer_hand = [pop_card(deck), pop_card(deck)]
    d_initial = dealer_hand[:]
    up = dealer_hand[0]
    
    conn.execute("DELETE FROM bj_hands")

    for u, br, bm, bp, b213 in players:
        bm, bp, b213, br = int(bm or 0), int(bp or 0), int(b213 or 0), int(br or 0)
        p_hand = [pop_card(deck), pop_card(deck)]
        p_score = calculate_score(p_hand)
        total_bet = bm + bp + b213
        br -= total_bet
        
        side_msgs = []
        if bp > 0:
            mult, lbl = settle_pair(p_hand)
            if mult > 0: br += int(bp * (mult + 1)); side_msgs.append(lbl)
        if b213 > 0:
            mult, lbl = settle_21p3(p_hand, up)
            if mult > 0: br += int(b213 * (mult + 1)); side_msgs.append(lbl)
            
        p_status = "PLAYING"
        if p_score == 21: p_status = "STAND"

        conn.execute("UPDATE bj_players SET status='PLAYING', bankroll=?, side_result=?, main_result='', insurance_bet=0, insurance_taken=0 WHERE username=?", (br, " | ".join(side_msgs), u))
        conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 0, ?, ?, ?, ?, 0, 0)", (u, json.dumps(p_hand), p_score, p_status, bm))

    dealer_has_blackjack = is_blackjack(d_initial)
    up_rank = up['rank']
    up_is_ten = up_rank in ['10','J','Q','K']
    is_ace_up = is_ace(up)

    next_status = 'PLAYING'
    if is_ace_up: next_status = 'INSURANCE'

    conn.execute("UPDATE bj_game SET status=?, deck=?, dealer_hand=?, dealer_initial_hand=?, current_player_index=0, current_hand_index=0 WHERE id=1", (next_status, json.dumps(deck), json.dumps(dealer_hand), json.dumps(d_initial)))
    conn.commit()

    if dealer_has_blackjack and up_is_ten:
        conn.close(); end_round(); return True, "Banco Blackjack! Partita terminata."
    
    conn.close()
    if next_status == 'PLAYING': next_turn_logic()
    return True, "Partita iniziata"

def close_insurance_phase(username):
    conn = get_connection()
    seated = conn.execute("SELECT 1 FROM bj_players WHERE username=?", (username,)).fetchone()
    if not seated: conn.close(); return False, "Non sei seduto al tavolo."

    d_initial_json = conn.execute("SELECT dealer_initial_hand FROM bj_game WHERE id=1").fetchone()[0]
    d_initial = json.loads(d_initial_json)
    
    if is_blackjack(d_initial):
        conn.close(); end_round(); return True, "Banco ha Blackjack!"
    else:
        conn.execute("UPDATE bj_game SET status='PLAYING' WHERE id=1")
        conn.commit(); conn.close(); next_turn(); return False, "Niente Blackjack, si gioca!"

def next_turn_logic():
    next_turn()

def next_turn():
    conn = get_connection()
    players = conn.execute("SELECT username FROM bj_players ORDER BY rowid").fetchall()
    if not players: conn.close(); return

    curr_p_idx, curr_h_idx = conn.execute("SELECT current_player_index, current_hand_index FROM bj_game WHERE id=1").fetchone()
    
    for i in range(curr_p_idx, len(players)):
        user = players[i][0]
        start_h = curr_h_idx if i == curr_p_idx else 0
        hands = conn.execute("SELECT hand_index FROM bj_hands WHERE username=? AND status='PLAYING' AND hand_index >= ? ORDER BY hand_index", (user, start_h)).fetchone()
        if hands:
            conn.execute("UPDATE bj_game SET current_player_index=?, current_hand_index=? WHERE id=1", (i, hands[0]))
            conn.commit(); conn.close(); return

    for i in range(0, curr_p_idx + 1):
        user = players[i][0]
        end_h_limit = 999 if i != curr_p_idx else curr_h_idx
        hands = conn.execute("SELECT hand_index FROM bj_hands WHERE username=? AND status='PLAYING' AND hand_index < ? ORDER BY hand_index", (user, end_h_limit)).fetchone()
        if hands:
            conn.execute("UPDATE bj_game SET current_player_index=?, current_hand_index=? WHERE id=1", (i, hands[0]))
            conn.commit(); conn.close(); return
            
    conn.commit(); conn.close(); end_round()

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
    conn.commit(); conn.close(); next_turn()

def player_double(username):
    conn = get_connection()
    turn_user, _, h_idx = get_current_turn(conn)
    if turn_user != username: conn.close(); return "NOT_YOUR_TURN"
    hand_row = conn.execute("SELECT hand, bet, doubled, status FROM bj_hands WHERE username=? AND hand_index=?", (username, h_idx)).fetchone()
    hand = json.loads(hand_row[0]); bet = int(hand_row[1]); doubled = int(hand_row[2]); status = hand_row[3]
    if len(hand) != 2 or doubled == 1 or status != "PLAYING": conn.close(); return "NOT_ALLOWED"
    bankroll = int(conn.execute("SELECT bankroll FROM bj_players WHERE username=?", (username,)).fetchone()[0])
    if bankroll < bet: conn.close(); return "NO_MONEY"
    deck = json.loads(conn.execute("SELECT deck FROM bj_game WHERE id=1").fetchone()[0])
    bankroll -= bet
    hand.append(pop_card(deck))
    score = calculate_score(hand)
    status = "STAND"
    if score > 21: status = "BUST"
    conn.execute("UPDATE bj_players SET bankroll=? WHERE username=?", (bankroll, username))
    conn.execute("UPDATE bj_hands SET hand=?, score=?, status=?, bet=?, doubled=1 WHERE username=? AND hand_index=?", (json.dumps(hand), score, status, bet*2, username, h_idx))
    conn.execute("UPDATE bj_game SET deck=? WHERE id=1", (json.dumps(deck),))
    conn.commit(); conn.close(); next_turn(); return "OK"

def player_split(username):
    conn = get_connection()
    turn_user, _, h_idx = get_current_turn(conn)
    if turn_user != username or h_idx != 0: conn.close(); return "NOT_ALLOWED"
    cnt = conn.execute("SELECT count(*) FROM bj_hands WHERE username=?", (username,)).fetchone()[0]
    if cnt > 1: conn.close(); return "MAX_SPLIT"
    hand_row = conn.execute("SELECT hand, bet FROM bj_hands WHERE username=? AND hand_index=?", (username, h_idx)).fetchone()
    hand = json.loads(hand_row[0]); bet = int(hand_row[1])
    if len(hand) != 2 or not is_pair_for_split(hand): conn.close(); return "NOT_PAIR"
    bankroll = int(conn.execute("SELECT bankroll FROM bj_players WHERE username=?", (username,)).fetchone()[0])
    if bankroll < bet: conn.close(); return "NO_MONEY"
    deck = json.loads(conn.execute("SELECT deck FROM bj_game WHERE id=1").fetchone()[0])
    
    c1 = hand[0]; c2 = hand[1]
    h1 = [c1, pop_card(deck)]
    h2 = [c2, pop_card(deck)]
    split_aces = (c1['rank'] == 'A' and c2['rank'] == 'A')
    status_after = "STAND" if split_aces else "PLAYING"
    
    bankroll -= bet
    conn.execute("UPDATE bj_players SET bankroll=? WHERE username=?", (bankroll, username))
    conn.execute("UPDATE bj_hands SET hand=?, score=?, status=?, is_split_hand=1 WHERE username=? AND hand_index=0", (json.dumps(h1), calculate_score(h1), status_after, username))
    conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 1, ?, ?, ?, ?, 0, 1)", (username, json.dumps(h2), calculate_score(h2), status_after, bet))
    conn.execute("UPDATE bj_game SET deck=? WHERE id=1", (json.dumps(deck),))
    conn.commit(); conn.close()
    if split_aces: next_turn()
    return "OK"

def player_insurance(username, amount):
    conn = get_connection()
    if not can_take_insurance_strict(conn, username): conn.close(); return "NOT_ALLOWED"
    bankroll = int(conn.execute("SELECT bankroll FROM bj_players WHERE username=?", (username,)).fetchone()[0])
    if bankroll < amount: conn.close(); return "NO_MONEY"
    bankroll -= amount
    conn.execute("UPDATE bj_players SET bankroll=?, insurance_bet=?, insurance_taken=1 WHERE username=?", (bankroll, amount, username))
    conn.commit(); conn.close(); return "OK"

def end_round():
    conn = get_connection()
    game = conn.execute("SELECT deck, dealer_hand, dealer_initial_hand FROM bj_game WHERE id=1").fetchone()
    deck = json.loads(game[0])
    d_hand = json.loads(game[1])
    d_initial = json.loads(game[2])
    d_score = calculate_score(d_hand)
    while d_score < 17:
        d_hand.append(pop_card(deck))
        d_score = calculate_score(d_hand)
    dealer_bj = is_blackjack(d_initial)
    players = conn.execute("SELECT username, bankroll, insurance_bet FROM bj_players").fetchall()
    for u, br, ins in players:
        br = int(br); ins = int(ins)
        if ins > 0 and dealer_bj: br += ins * 3
        hands = conn.execute("SELECT hand, score, status, bet, is_split_hand FROM bj_hands WHERE username=?", (u,)).fetchall()
        res_str = []
        for h_json, sc, stt, bet, is_split in hands:
            bet = int(bet); hand = json.loads(h_json); p_bj = is_blackjack(hand)
            outcome = "Perso"
            if stt == 'BUST': outcome = "Sballato"
            else:
                if dealer_bj:
                    if p_bj:
                        if not is_split: outcome = "Push"; br += bet
                        else: outcome = "Banco BJ"
                    else: outcome = "Banco BJ"
                elif p_bj:
                    if not is_split: outcome = "Blackjack!"; br += int(bet * 2.5)
                    else: outcome = "21 (Split)"; br += bet * 2
                elif d_score > 21: outcome = "Vinto"; br += bet * 2
                elif sc > d_score: outcome = "Vinto"; br += bet * 2
                elif sc == d_score: outcome = "Push"; br += bet
            res_str.append(outcome)
        conn.execute("UPDATE bj_players SET bankroll=?, main_result=? WHERE username=?", (br, " | ".join(res_str), u))
    conn.execute("UPDATE bj_game SET dealer_hand=?, status='FINISHED' WHERE id=1", (json.dumps(d_hand),))
    conn.commit(); conn.close()

def reset_round():
    conn = get_connection()
    conn.execute("UPDATE bj_game SET status='WAITING', dealer_hand='[]', dealer_initial_hand='[]', current_player_index=0, current_hand_index=0 WHERE id=1")
    conn.execute("UPDATE bj_players SET status='READY', insurance_bet=0, insurance_taken=0, side_result='', main_result=''")
    conn.execute("DELETE FROM bj_hands")
    users = conn.execute("SELECT username FROM bj_players").fetchall()
    for u in users:
        conn.execute("INSERT INTO bj_hands (username, hand_index, hand, score, status, bet, doubled, is_split_hand) VALUES (?, 0, '[]', 0, 'READY', 0, 0, 0)", (u[0],))
    conn.commit(); conn.close()

def render_card_span(card):
    if not card: return ""
    r = card["rank"]; s = card["suit"]
    color_class = "card-red" if s in ["♥", "♦"] else "card-black"
    return f"<span class='game-card {color_class}'>{r}{s}</span>"

# --- INTERFACCIA GIOCO ---
def blackjack_section():
    if not st.session_state.get("logged_in"):
        st.warning("Devi fare login."); st.stop()
    
    init_blackjack_db()
    
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.title("🎰 Terrazzo Casino")
    
    username = st.session_state.username
    conn = get_connection()
    game_state = conn.execute("SELECT status, dealer_hand, current_player_index FROM bj_game WHERE id=1").fetchone()
    players_data = conn.execute("SELECT username, bankroll, bet_main, bet_pair, bet_21p3, side_result, main_result, insurance_taken FROM bj_players ORDER BY rowid").fetchall()
    status, d_hand_json, curr_idx = game_state
    d_hand = json.loads(d_hand_json or "[]")
    is_seated = any(p[0] == username for p in players_data)
    
    # helper turn info
    curr_p_name = curr_p_idx = curr_h_idx = None
    if status == 'PLAYING':
        curr_p_name, curr_p_idx, curr_h_idx = get_current_turn(conn)
    conn.close()

    # --- LOBBY ---
    if status == 'WAITING':
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 🛋️ Al tavolo:")
            if not players_data: st.write("Tavolo vuoto.")
            for p in players_data: st.write(f"👤 {p[0]} (🪙 {p[1]})")
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
            bm = c_m.number_input("Main", value=int(me[1] or 0), step=10, min_value=0)
            bp = c_p.number_input("Pair", value=int(me[2] or 0), step=5, min_value=0)
            bs = c_s.number_input("21+3", value=int(me[3] or 0), step=5, min_value=0)
            
            if st.button("Salva Puntate"):
                conn = get_connection()
                conn.execute("UPDATE bj_players SET bet_main=?, bet_pair=?, bet_21p3=? WHERE username=?", (bm, bp, bs, username))
                conn.commit(); conn.close()
                st.success("Salvato!")
                time.sleep(0.3); st.rerun()
                
            if st.button("🚀 START GAME"):
                ok, msg = start_game()
                if ok: st.rerun()
                else: st.error(msg)
        
        time.sleep(2); st.rerun()

    # --- GIOCO ---
    else:
        st.write("### 🎩 Dealer")
        cols = st.columns(6)
        d_score = "?"
        if status == 'FINISHED': d_score = calculate_score(d_hand)
        
        for i, card in enumerate(d_hand):
            if (status in ["PLAYING", "INSURANCE"]) and i == 1:
                cols[i].markdown("<div class='game-card card-black'>🂠</div>", unsafe_allow_html=True)
            else:
                cols[i].markdown(render_card_span(card), unsafe_allow_html=True)
        st.caption(f"Punti: {d_score}")
        
        if status == 'INSURANCE':
            st.markdown("<span class='status-badge status-insurance'>INSURANCE</span>", unsafe_allow_html=True)
            st.warning("⚠️ Il banco ha un Asso!")
        
        st.divider()
        
        # PLAYERS UI
        conn = get_connection()
        p_cols = st.columns(len(players_data) if players_data else 1)
        for i, p_data in enumerate(players_data):
            p_name = p_data[0]
            hands = conn.execute("SELECT hand_index, hand, score, status, bet FROM bj_hands WHERE username=? ORDER BY hand_index", (p_name,)).fetchall()
            with p_cols[i]:
                st.write(f"**{p_name}**")
                st.caption(f"🪙 {p_data[1]}")
                if p_data[5]: st.info(f"Side: {p_data[5]}")
                if status == "FINISHED" and p_data[6]: st.success(p_data[6])
                if int(p_data[7] or 0) == 1: st.caption("🛡️ Insured")
                
                for idx, h_json, sc, stt, bt in hands:
                    hand_cards = json.loads(h_json or "[]")
                    is_active = (status == "PLAYING" and p_name == curr_p_name and idx == curr_h_idx)
                    bg = "background-color: #eff6ff; border: 2px solid #3b82f6;" if is_active else ""
                    st.markdown(f"<div style='padding:6px; border-radius:10px; {bg}'>", unsafe_allow_html=True)
                    if hand_cards: st.markdown("".join(render_card_span(c) for c in hand_cards), unsafe_allow_html=True)
                    st.caption(f"Bet: {bt} | Punti: {sc}")
                    if stt != "PLAYING": st.caption(f"*{stt}*")
                    st.markdown("</div>", unsafe_allow_html=True)
        conn.close()
        
        # ACTIONS
        if status == 'INSURANCE':
            st.write("---")
            if is_seated:
                conn = get_connection()
                if can_take_insurance_strict(conn, username):
                     bet0 = int(conn.execute("SELECT bet FROM bj_hands WHERE username=? AND hand_index=0", (username,)).fetchone()[0])
                     if st.button(f"Compra Insurance ({bet0//2})"):
                         player_insurance(username, bet0//2); st.rerun()
                conn.close()
                if st.button("➡️ Continua"):
                    end, msg = close_insurance_phase(username)
                    if end: st.error(msg)
                    st.rerun()

        elif status == 'PLAYING' and username == curr_p_name:
            st.write("---")
            st.markdown("### 🔥 Tocca a te!")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("HIT 🃏"): player_hit(username); st.rerun()
            if c2.button("STAND ✋"): player_stand(username); st.rerun()
            if c3.button("DOUBLE 2️⃣"): 
                if player_double(username) != "OK": st.error("Non puoi raddoppiare")
                else: st.rerun()
            if c4.button("SPLIT ✂️"): 
                if player_split(username) != "OK": st.error("Non puoi splittare")
                else: st.rerun()

        elif status == 'FINISHED':
            st.write("---")
            if st.button("Rigioca 🔄"): reset_round(); st.rerun()
        else:
            time.sleep(2); st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)
