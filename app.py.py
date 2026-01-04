import streamlit as st
import sqlite3
import datetime
import time
import hashlib
import json
from urllib.request import urlopen

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Terrazzo Booking", layout="centered")

# --- CUSTOM CSS (Apple Style Clean) ---
def local_css():
    st.markdown("""
    <style>
    /* IMPORT FONT INTER */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* APP GENERALE */
    .stApp {
        background-color: #f8fafc;
        background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
        background-size: 24px 24px;
        color: #0f172a;
        font-family: 'Inter', sans-serif;
    }

    /* CONTENUTO CENTRALE */
    .block-container {
        max-width: 1000px;
        padding-top: 3rem;
        padding-bottom: 5rem;
    }

    /* CARD STANDARD (Glassmorphism) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.2s ease;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }

    /* TITOLI */
    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #0f172a;
    }

    /* PANNELLO ADMIN */
    .admin-card {
        background: #ffffff;
        border-radius: 24px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid #e2e8f0;
    }

    /* PULSANTI (Gradient Glow) */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
        color: white !important;
        border-radius: 12px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
        transition: all 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
    }

    /* LINK BUTTON SECONDARIO */
    a[href^="http"] button {
        background: white !important;
        color: #2563eb !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: none !important;
    }
    a[href^="http"] button:hover {
        border-color: #2563eb !important;
        background: #f8fafc !important;
    }
    
    /* PROGRESS BAR */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #0ea5e9, #2563eb);
        border-radius: 10px;
    }

    /* INPUT FIELDS */
    input[type="text"], input[type="number"], input[type="password"], textarea {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        color: #0f172a !important;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f1f5f9;
        padding-top: 1rem;
    }

    /* Titolo Sidebar */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        font-size: 1.2rem;
        margin-bottom: 0;
    }

    /* Menu di navigazione */
    .stRadio > label { display: none; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child { display: none; }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        padding: 10px 16px;
        border-radius: 12px;
        margin-bottom: 4px;
        border: 1px solid transparent;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background-color: #f8fafc;
        border-color: #e2e8f0;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #eff6ff;
        border-color: #bfdbfe;
        color: #1d4ed8;
        font-weight: 600;
    }
    
    /* ACCOUNT DROPDOWN STYLE (Expander) */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: none;
        box-shadow: none;
        background-color: transparent;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] details {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        background-color: #fff;
    }
    
    /* CHAT BUBBLES MODERNE */
    .chat-row {
        display: flex;
        width: 100%;
        margin-bottom: 12px;
        align-items: flex-end;
    }
    .chat-row.right {
        justify-content: flex-end;
    }
    .chat-row.left {
        justify-content: flex-start;
    }
    
    .chat-bubble {
        padding: 12px 18px;
        border-radius: 20px;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.4;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        position: relative;
    }
    .chat-bubble.me {
        background: linear-gradient(135deg, #0ea5e9, #2563eb);
        color: white;
        border-bottom-right-radius: 4px;
    }
    .chat-bubble.other {
        background-color: #f1f5f9;
        color: #1e293b;
        border: 1px solid #e2e8f0;
        border-bottom-left-radius: 4px;
    }
    .chat-user-label {
        font-size: 0.75rem;
        color: #64748b;
        margin-left: 14px;
        margin-bottom: 4px;
        font-weight: 600;
    }

    /* COUNTDOWN & ALERT */
    .countdown-text {
        font-size: 0.9rem;
        font-weight: 600;
        color: #64748b;
        background: #f1f5f9;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 0.8rem;
    }
    .countdown-urgent {
        color: #ef4444;
        background: #fee2e2;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.85; transform: scale(0.98); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    /* Box Meteo nella Sidebar */
    [data-testid="stMetric"] {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* FAST TRACK UI */
    .fast-track-box {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
        border: 2px solid #3b82f6;
        border-radius: 24px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        margin-bottom: 2rem;
    }
    .fast-track-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
    }
    
    /* ADMIN SECTIONS */
    .admin-section {
        background-color: #F9FAFB;
        border-radius: 14px;
        border: 1px solid #E5E7EB;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .admin-section-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# DATABASE
DB_NAME = 'terrazzo_vito.db' 
LINK_REVOLUT = "https://revolut.me/gianlunapolano"
VITO_ADDRESS = "Via Arenella, 95, 80128 Napoli NA"
VITO_MAP_URL = "https://www.google.com/maps/search/?api=1&query=Via+Arenella+95+Napoli"

# --- SICUREZZA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# --- METEO ---
def get_weather_napoli_live():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=40.8518&longitude=14.2681&current_weather=true"
        response = urlopen(url)
        data = json.loads(response.read())
        temp = data['current_weather']['temperature']
        wcode = data['current_weather']['weathercode']
        wind = data['current_weather']['windspeed']
        icon = "☀️"
        if wcode in [1, 2, 3]: icon = "⛅"
        elif wcode >= 51: icon = "🌧️"
        return f"{icon} {temp}°C", f"Vento: {wind} km/h"
    except:
        return "🌡️ N/D", "-"

def get_forecast_for_date(date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude=40.8518&longitude=14.2681&daily=weathercode,temperature_2m_max&timezone=auto&start_date={date_str}&end_date={date_str}"
        response = urlopen(url)
        data = json.loads(response.read())
        if 'daily' in data and 'weathercode' in data['daily']:
            wcode = data['daily']['weathercode'][0]
            temp_max = data['daily']['temperature_2m_max'][0]
            return (wcode >= 51), temp_max
    except:
        return False, None

# --- DB INIT ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS slots (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, tema TEXT, creator TEXT, description TEXT, is_confirmed INTEGER DEFAULT 1, UNIQUE(data, ora))''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, nome_amico TEXT, note TEXT, plus_one INTEGER DEFAULT 0, nome_plus_one TEXT, tieni_status INTEGER DEFAULT 0, FOREIGN KEY(slot_id) REFERENCES slots(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS donazioni (id INTEGER PRIMARY KEY AUTOINCREMENT, donatore TEXT, importo REAL, username TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS goal (id INTEGER PRIMARY KEY, description TEXT, target REAL, current REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bringing (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, username TEXT, item TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS waitlist (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, username TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS event_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER, username TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    if c.execute("SELECT count(*) FROM goal").fetchone()[0] == 0:
        c.execute("INSERT INTO goal (id, description, target, current) VALUES (1, 'Fondo Serate', 100.0, 0.0)")
        conn.commit()
    
    # MIGRATIONS
    try: c.execute("ALTER TABLE bookings ADD COLUMN nome_plus_one TEXT")
    except: pass
    try: c.execute("ALTER TABLE bookings ADD COLUMN tieni_status INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE slots ADD COLUMN creator TEXT")
    except: pass
    try: c.execute("ALTER TABLE slots ADD COLUMN description TEXT")
    except: pass
    try: c.execute("ALTER TABLE slots ADD COLUMN is_confirmed INTEGER DEFAULT 1")
    except: pass
    try: c.execute("ALTER TABLE donazioni ADD COLUMN username TEXT")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN role TEXT")
    except: pass

    conn.commit()
    conn.close()

init_db()

# --- GESTIONE RUOLI ---
def assign_user_role(username, role):
    conn = get_connection()
    conn.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
    conn.commit()
    conn.close()

def get_user_role_badge(username):
    if not username: return ""
    conn = get_connection()
    role = conn.execute("SELECT role FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if role and role[0]:
        r = role[0]
        style = "background-color: #E0F2FE; color: #0284C7; border: 1px solid #7DD3FC;"
        if "DJ" in r: style = "background-color: #F3E8FF; color: #9333EA; border: 1px solid #D8B4FE;"
        elif "Barman" in r: style = "background-color: #FEF3C7; color: #D97706; border: 1px solid #FCD34D;"
        elif "Admin" in r or "Boss" in r: style = "background-color: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5;"
        elif "VIP" in r or "Re" in r: style = "background: linear-gradient(45deg, #FFD700, #FDB931); color: #FFF; text-shadow: 0 1px 2px rgba(0,0,0,0.2);"
        return f"<span class='role-badge' style='{style}'>{r}</span>"
    return ""

def is_user_booked(slot_id, username):
    if not username: return False
    conn = get_connection()
    res = conn.execute("SELECT count(*) FROM bookings WHERE slot_id=? AND nome_amico=?", (slot_id, username)).fetchone()[0]
    conn.close()
    return res > 0

def cleanup_past_events():
    conn = get_connection()
    slots = conn.execute("SELECT id, data, ora FROM slots").fetchall()
    now = datetime.datetime.now()
    deleted = False
    for s in slots:
        try:
            event_dt = datetime.datetime.strptime(f"{s[1]} {s[2]}", "%Y-%m-%d %H:%M:%S")
            if now > event_dt:
                conn.execute("DELETE FROM bookings WHERE slot_id=?", (s[0],))
                conn.execute("DELETE FROM bringing WHERE slot_id=?", (s[0],))
                conn.execute("DELETE FROM waitlist WHERE slot_id=?", (s[0],))
                conn.execute("DELETE FROM event_messages WHERE slot_id=?", (s[0],))
                conn.execute("DELETE FROM slots WHERE id=?", (s[0],))
                deleted = True
        except: pass
    if deleted:
        conn.commit()
    conn.close()

def get_total_donations():
    conn = get_connection()
    res = conn.execute("SELECT SUM(importo) FROM donazioni").fetchone()[0]
    conn.close()
    return res if res else 0.0

def get_target():
    conn = get_connection()
    res = conn.execute("SELECT target, description FROM goal WHERE id=1").fetchone()
    conn.close()
    return res

def add_donation(nome, importo):
    conn = get_connection()
    conn.execute("INSERT INTO donazioni (donatore, importo) VALUES (?, ?)", (nome, importo))
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, make_hashes(password)))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def login_user(username, password):
    conn = get_connection()
    data = conn.execute("SELECT password FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if data: return check_hashes(password, data[0])
    return False

# --- LOGICA FAST TRACK (FLUSSO A) ---
def get_next_available_slot():
    conn = get_connection()
    slot = conn.execute("SELECT id, data, ora, tema FROM slots WHERE is_confirmed=1 ORDER BY data, ora LIMIT 1").fetchone()
    conn.close()
    
    if slot:
        conn = get_connection()
        taken = conn.execute("SELECT count(*) + sum(plus_one) FROM bookings WHERE slot_id=?", (slot[0],)).fetchone()[0] or 0
        conn.close()
        if taken < 10:
            return slot
    return None

def handle_fast_track():
    if "action" in st.query_params and st.query_params["action"] == "fastjoin":
        st.markdown("""<style>[data-testid="stSidebar"] {display: none;} .block-container {max-width: 600px; padding-top: 2rem;}</style>""", unsafe_allow_html=True)
        slot = get_next_available_slot()
        st.markdown('<div class="fast-track-box">', unsafe_allow_html=True)
        st.markdown('<div class="fast-track-title">🚀 Fast Booking Terrazzo</div>', unsafe_allow_html=True)
        
        if not slot:
            st.error("Nessun evento disponibile o posti esauriti! 😔")
            if st.button("Vai alla Home"):
                st.query_params.clear()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            return True

        sid, s_d, s_o, s_t = slot
        st.info(f"Prossimo Evento:\n\n**{s_t}**\n\n📅 {s_d} ore {s_o}")
        
        if st.session_state.logged_in:
            if is_user_booked(sid, st.session_state.username):
                st.success(f"✅ Sei già prenotato, {st.session_state.username}!")
            else:
                conn = get_connection()
                conn.execute("INSERT INTO bookings (slot_id, nome_amico, note, plus_one, nome_plus_one, tieni_status) VALUES (?, ?, ?, 0, '', 1)", 
                             (sid, st.session_state.username, "Fast Booking ⚡"))
                conn.commit()
                conn.close()
                st.balloons()
                st.success(f"✅ Prenotazione Confermata per {st.session_state.username}!")
            
            st.write("---")
            with st.expander("📝 Aggiungi +1 o Note (Opzionale)"):
                with st.form("fast_upd"):
                    note = st.text_input("Note")
                    p1 = st.checkbox("Porto +1")
                    np1 = ""
                    if p1: np1 = st.text_input("Nome +1")
                    if st.form_submit_button("Salva Dettagli"):
                        conn = get_connection()
                        conn.execute("UPDATE bookings SET note=?, plus_one=?, nome_plus_one=? WHERE slot_id=? AND nome_amico=?", 
                                     (note, 1 if p1 else 0, np1, sid, st.session_state.username))
                        conn.commit()
                        conn.close()
                        st.toast("Salvato!")
            
            if st.button("Vai alla Home"):
                st.query_params.clear()
                st.rerun()
        else:
            st.write("Chi sei?")
            with st.form("fast_login_form"):
                name = st.text_input("Il tuo nome", placeholder="Es. Marco")
                if st.form_submit_button("Ci sono! 🚀"):
                    if name:
                        conn = get_connection()
                        exists = conn.execute("SELECT count(*) FROM users WHERE username=?", (name,)).fetchone()[0]
                        conn.close()
                        if not exists: create_user(name, "terrazzo")
                        st.session_state.logged_in = True
                        st.session_state.username = name
                        st.rerun()
                    else:
                        st.error("Inserisci il nome!")
        
        st.markdown('</div>', unsafe_allow_html=True)
        return True
    return False

# --- MAIN ---
def main():
    local_css()
    cleanup_past_events()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    if handle_fast_track():
        return

    with st.sidebar:
        if st.session_state.logged_in:
            with st.expander("👤  Account", expanded=False):
                role_html = get_user_role_badge(st.session_state.username)
                st.markdown(f"Utente: **{st.session_state.username}** {role_html}", unsafe_allow_html=True)
                if st.button("Esci (Logout)", use_container_width=True):
                    st.session_state.logged_in = False
                    st.session_state.username = None
                    st.rerun()
        else:
            st.info("Accedi per prenotare.")

        st.divider()
        menu_options = ["🔒  Area Admin"]
        if st.session_state.logged_in:
            menu_options = ["🏠  Bacheca Eventi", "📅  I Miei Eventi", "🎂  Organizza Party", "🔒  Area Admin"]
        else:
            menu_options = ["🔑  Accedi / Registrati", "🔒  Area Admin"]
        
        mode = st.sidebar.radio("Navigazione", menu_options, label_visibility="collapsed")
        
        st.divider()
        temp_val, weather_desc = get_weather_napoli_live()
        st.metric("Meteo Napoli", temp_val, weather_desc)
        
        st.markdown("<br>", unsafe_allow_html=True)
        target, desc = get_target()
        totale = get_total_donations()
        st.markdown(f"**🎯 {desc}**")
        progress_val = max(0.0, min(totale / target, 1.0)) if target > 0 else 0
        st.progress(progress_val)
        st.caption(f"Raccolti: {totale}€ su {target}€")
        st.sidebar.link_button("💜 Supporta il progetto", LINK_REVOLUT, use_container_width=True)

        st.divider()
        st.caption("📍 Quick Link")
        if st.button("Vai da Vito fratm 🛵", use_container_width=True):
            st.warning(f"📍 {VITO_ADDRESS}")
            st.link_button("Apri Mappa", VITO_MAP_URL)
            st.snow()

    if mode == "🔒  Area Admin": admin_section()
    elif mode == "🏠  Bacheca Eventi": user_section()
    elif mode == "📅  I Miei Eventi": my_bookings_section()
    elif mode == "🎂  Organizza Party": birthday_section()
    elif mode == "🔑  Accedi / Registrati": auth_section()

# --- SEZIONI ---

def auth_section():
    st.title("Benvenuto nel Club 🔒")
    st.markdown("Questa è un'area privata. Accedi o crea un account per prenotare.")
    tab_login, tab_register = st.tabs(["Accedi", "Registrati"])
    
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Entra"):
                if login_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Accesso effettuato!")
                    st.rerun()
                else:
                    st.error("Credenziali errate.")

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("Scegli un Username")
            new_pass = st.text_input("Scegli una Password", type="password")
            if st.form_submit_button("Crea Account"):
                if create_user(new_user, new_pass):
                    st.success("Account creato! Vai su Accedi.")
                else:
                    st.error("Username già in uso.")

def my_bookings_section():
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.title("Le mie Prenotazioni 📅")
    
    conn = get_connection()
    my_books = conn.execute("""
        SELECT s.data, s.ora, s.tema, b.plus_one, b.nome_plus_one, b.note, b.id, s.id, s.is_confirmed
        FROM bookings b JOIN slots s ON b.slot_id = s.id 
        WHERE b.nome_amico = ? ORDER BY s.data, s.ora
    """, (st.session_state.username,)).fetchall()
    conn.close()

    if my_books:
        for b in my_books:
            data, ora, tema, p1, np1, note, bid, slot_id, is_conf = b
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    status_text = " (⏳ IN ATTESA DI APPROVAZIONE)" if is_conf == 0 else ""
                    st.subheader(f"{data} | {ora}{status_text}")
                    st.markdown(f"**{tema}**")
                    if p1: st.caption(f"👯 +1: {np1}")
                    if note: st.caption(f"📝 {note}")
                with c2:
                    st.write("")
                    if st.button("Disdici", key=f"cancel_my_{bid}"):
                        conn = get_connection()
                        conn.execute("DELETE FROM bookings WHERE id=?", (bid,))
                        conn.commit()
                        st.toast("Cancellata.")
                        st.rerun()
                
                if is_conf == 1:
                    with st.expander("💬 Apri Chat"):
                        conn = get_connection()
                        msgs = conn.execute("SELECT id, username, message FROM event_messages WHERE slot_id=? ORDER BY id", (slot_id,)).fetchall()
                        conn.close()
                        
                        if msgs:
                            for m in msgs:
                                msg_id, user, message = m
                                is_me = (user == st.session_state.username)
                                align = "right" if is_me else "left"
                                bubble = "me" if is_me else "other"
                                role_html = get_user_role_badge(user)
                                st.markdown(f"""<div style='overflow:hidden; padding:2px;'><div style='float:{align};' class='chat-bubble {bubble}'><b>{user} {role_html}:</b> {message}</div></div>""", unsafe_allow_html=True)
                                if is_me:
                                    if st.button("🗑️", key=f"del_msg_my_{msg_id}"):
                                        conn = get_connection()
                                        conn.execute("DELETE FROM event_messages WHERE id=?", (msg_id,))
                                        conn.commit()
                                        st.rerun()
                        
                        c_msg, c_send = st.columns([4, 1])
                        new_msg = c_msg.text_input("Messaggio...", key=f"chat_{slot_id}", label_visibility="collapsed")
                        if c_send.button("Invia", key=f"snd_{slot_id}"):
                            conn = get_connection()
                            conn.execute("INSERT INTO event_messages (slot_id, username, message) VALUES (?, ?, ?)", (slot_id, st.session_state.username, new_msg))
                            conn.commit()
                            st.rerun()
                else:
                    st.info("Chat bloccata: evento in attesa.")
    else:
        st.info("Non hai prenotazioni attive.")
    st.markdown('</div>', unsafe_allow_html=True)

def birthday_section():
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.title("Organizza Compleanno 🎂")
    
    with st.form("create_birthday"):
        c1, c2 = st.columns(2)
        b_date = c1.date_input("Data", min_value=datetime.date.today())
        b_time = c2.time_input("Ora", value=datetime.time(20, 0))
        b_theme = st.text_input("Titolo Evento", value=f"Compleanno di {st.session_state.username}")
        b_desc = st.text_area("Dettagli", placeholder="Info utili...")
        
        st.info("💰 Versa 5€ al fondo cassa per confermare.")
        st.link_button("Invia 5€ (Revolut)", LINK_REVOLUT)
        paid = st.checkbox("Ho inviato il contributo (L'Admin verificherà)", value=False, key="pay_check")
        
        st.write("---")
        st.write("**👥 Quanti amici porti?**")
        # SLIDER PER SELEZIONARE IL NUMERO DI OSPITI (Max 9 + 1)
        guest_count = st.slider("Numero di ospiti (Escluso te)", min_value=0, max_value=9, value=0)
        st.caption(f"Totale prenotazione: **{guest_count + 1}** persone (Tu + {guest_count} ospiti).")
        
        if st.form_submit_button("Invia Richiesta 🎉"):
            if not paid:
                st.error("Devi confermare di aver inviato il contributo di 5€!")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO slots (data, ora, tema, creator, description, is_confirmed) VALUES (?, ?, ?, ?, ?, 0)", 
                                 (str(b_date), str(b_time), b_theme, st.session_state.username, b_desc))
                    sid = cur.lastrowid
                    
                    # 1. Prenota Festeggiato
                    cur.execute("INSERT INTO bookings (slot_id, nome_amico, note, plus_one, nome_plus_one, tieni_status) VALUES (?, ?, ?, ?, ?, ?)", 
                                    (sid, st.session_state.username, "Festeggiato 👑", 0, "", 1))
                    
                    # 2. Prenota Ospiti generici
                    if guest_count > 0:
                        for i in range(guest_count):
                            g_name = f"Ospite {i+1} di {st.session_state.username}"
                            cur.execute("INSERT INTO bookings (slot_id, nome_amico, note, plus_one, nome_plus_one, tieni_status) VALUES (?, ?, ?, ?, ?, ?)", 
                                        (sid, g_name, "Invitato", 0, "", 1))
                    
                    conn.commit()
                    conn.close()
                    st.success("Richiesta inviata! Attendi approvazione.")
                    st.info("Il tuo evento è in attesa. L'Admin confermerà la ricezione del pagamento.")
                    time.sleep(3)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Esiste già un evento in questa data e ora!")
                except Exception as e:
                    st.error(f"Errore: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

def admin_section():
    st.title("Pannello Admin 🔒")
    if st.text_input("Password", type="password") == "admin123":
        st.success("Accesso Admin")
        
        # TAB AGGIORNATI CON GESTIONE RUOLI E LINK
        tab_cassa, tab_ruoli, tab_crea, tab_gestione, tab_link = st.tabs(["💰 Cassa", "👥 Ruoli", "➕ Crea", "📅 Eventi", "🔗 Link"])
        
        # --- TAB LINK RAPIDO ---
        with tab_link:
            st.markdown('<div class="admin-section">', unsafe_allow_html=True)
            st.markdown('<div class="admin-section-title">Generatore Link WhatsApp</div>', unsafe_allow_html=True)
            st.info("Incolla qui il link di Ngrok (quello che finisce con .ngrok-free.app) per creare il link di auto-prenotazione.")
            base_url = st.text_input("Link Ngrok:", placeholder="https://....ngrok-free.app")
            if base_url:
                if base_url.endswith("/"): base_url = base_url[:-1]
                final_link = f"{base_url}/?action=fastjoin"
                st.success("Copia questo link e mandalo agli amici:")
                st.code(final_link, language="text")
            st.markdown('</div>', unsafe_allow_html=True)

        with tab_ruoli:
            st.markdown('<div class="admin-section">', unsafe_allow_html=True)
            st.markdown('<div class="admin-section-title">Assegna Titoli e Ruoli</div>', unsafe_allow_html=True)
            
            conn = get_connection()
            all_users = [u[0] for u in conn.execute("SELECT username FROM users").fetchall()]
            conn.close()
            
            c_u, c_r, c_b = st.columns([2, 2, 1])
            sel_user = c_u.selectbox("Seleziona Utente", all_users)
            sel_role = c_r.selectbox("Scegli Ruolo", ["🎧 DJ", "🍹 Barman", "📸 Fotografo", "🛡️ Security", "👑 Re del Terrazzo", "🧹 Addetto Pulizie", "🍕 Responsabile Cibo", "Nessuno"])
            
            if c_b.button("Assegna Ruolo"):
                role_to_save = sel_role if sel_role != "Nessuno" else None
                assign_user_role(sel_user, role_to_save)
                st.success(f"Assegnato {sel_role} a {sel_user}")
                st.rerun()
                
            st.divider()
            st.caption("Utenti con ruoli attivi:")
            conn = get_connection()
            users_with_roles = conn.execute("SELECT username, role FROM users WHERE role IS NOT NULL").fetchall()
            conn.close()
            for u, r in users_with_roles:
                st.write(f"- **{u}**: {r}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab_cassa:
            conn = get_connection()
            tot = conn.execute("SELECT SUM(importo) FROM donazioni").fetchone()[0] or 0
            tgt = conn.execute("SELECT target FROM goal WHERE id=1").fetchone()[0]
            conn.close()
            c1, c2 = st.columns(2)
            c1.metric("Totale", f"{tot}€")
            c2.metric("Target", f"{tgt}€")
            
            with st.expander("Aggiungi Donazione"):
                dn = st.text_input("Nome")
                di = st.number_input("Euro", step=1.0)
                if st.button("Salva Donazione"):
                    add_donation(dn, di)
                    st.toast("Salvato")
                    st.rerun()
            
            with st.expander("Gestione Donatori"):
                conn = get_connection()
                dons = conn.execute("SELECT id, donatore, importo FROM donazioni").fetchall()
                conn.close()
                if dons:
                    for d in dons:
                        c_nm, c_val, c_del = st.columns([3, 2, 1])
                        c_nm.write(d[1])
                        c_val.write(f"{d[2]}€")
                        if c_del.button("❌", key=f"del_d_{d[0]}"):
                            conn = get_connection()
                            conn.execute("DELETE FROM donazioni WHERE id=?", (d[0],))
                            conn.commit()
                            st.rerun()

        with tab_crea:
            c1, c2 = st.columns(2)
            d = c1.date_input("Data")
            t = c2.time_input("Ora", value=datetime.time(20,0))
            th = st.text_input("Tema", "Aperitivo")
            if st.button("Crea Evento (Admin)"):
                try:
                    conn = get_connection()
                    conn.execute("INSERT INTO slots (data, ora, tema, creator, is_confirmed) VALUES (?, ?, ?, ?, 1)", (str(d), str(t), th, "Admin"))
                    conn.commit()
                    st.toast("Creato!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                except: st.error("Esiste già.")

        with tab_gestione:
            st.markdown("### 🔔 Richieste Pending")
            conn = get_connection()
            pending = conn.execute("SELECT id, data, ora, tema, creator FROM slots WHERE is_confirmed=0").fetchall()
            conn.close()
            if pending:
                for p in pending:
                    with st.container(border=True):
                        st.write(f"**{p[3]}** ({p[1]} {p[2]}) di *{p[4]}*")
                        c_ok, c_no = st.columns(2)
                        if c_ok.button("✅ Approva", key=f"ok_{p[0]}"):
                            conn = get_connection()
                            conn.execute("UPDATE slots SET is_confirmed=1 WHERE id=?", (p[0],))
                            conn.commit()
                            st.success("Evento approvato!")
                            st.rerun()
                        if c_no.button("❌ Rifiuta", key=f"no_{p[0]}"):
                            conn = get_connection()
                            conn.execute("DELETE FROM bookings WHERE slot_id=?", (p[0],))
                            conn.execute("DELETE FROM slots WHERE id=?", (p[0],))
                            conn.commit()
                            st.warning("Richiesta cancellata.")
                            st.rerun()
            else: st.caption("Nessuna richiesta.")
            
            st.divider()
            st.markdown("### 📅 Eventi Attivi")
            conn = get_connection()
            slots = conn.execute("SELECT id, data, ora, tema, creator, is_confirmed FROM slots ORDER BY data, ora").fetchall()
            conn.close()
            
            for s in slots:
                sid, s_d, s_o, s_t, s_c, s_conf = s
                lbl = " (PENDING)" if s_conf==0 else ""
                with st.expander(f"{s_d} {s_o} - {s_t} ({s_c}){lbl}"):
                    
                    conn = get_connection()
                    parts = conn.execute("SELECT id, nome_amico, note, plus_one, nome_plus_one FROM bookings WHERE slot_id=?", (sid,)).fetchall()
                    conn.close()
                    
                    if parts:
                        st.write("👥 **Partecipanti:**")
                        for p in parts:
                            bid, bname, bnote, bp1, bnp1 = p
                            c_info, c_del = st.columns([5, 1])
                            info_str = f"**{bname}**"
                            if bp1: info_str += f" (+1: {bnp1})"
                            if bnote: info_str += f" | 📝 {bnote}"
                            c_info.markdown(f"- {info_str}")
                            if c_del.button("❌", key=f"adm_del_user_{bid}", help="Rimuovi partecipante"):
                                conn = get_connection()
                                conn.execute("DELETE FROM bookings WHERE id=?", (bid,))
                                conn.commit()
                                st.toast(f"Rimosso {bname}")
                                st.rerun()
                        st.divider()
                    else:
                        st.caption("Nessuna prenotazione.")
                    
                    st.divider()
                    st.write("🛠️ **Gestione & Modifica**")
                    with st.form(key=f"edit_event_{sid}"):
                        col_edit_1, col_edit_2 = st.columns(2)
                        try:
                            date_val = datetime.datetime.strptime(s_d, "%Y-%m-%d").date()
                            time_val = datetime.datetime.strptime(s_o, "%H:%M:%S").time()
                        except:
                            date_val = datetime.date.today()
                            time_val = datetime.time(20, 0)
                            
                        new_d = col_edit_1.date_input("Data", value=date_val)
                        new_t = col_edit_2.time_input("Ora", value=time_val)
                        new_thm = st.text_input("Tema", value=s_t)
                        
                        if st.form_submit_button("💾 Salva Modifiche"):
                            conn = get_connection()
                            conn.execute("UPDATE slots SET data=?, ora=?, tema=? WHERE id=?", (str(new_d), str(new_t), new_thm, sid))
                            conn.commit()
                            conn.close()
                            st.toast("Evento Modificato!", icon="✅")
                            time.sleep(1)
                            st.rerun()

                    if st.button("🗑️ Elimina Intero Evento", key=f"adm_del_ev_{sid}"):
                        conn = get_connection()
                        conn.execute("DELETE FROM bookings WHERE slot_id=?", (sid,))
                        conn.execute("DELETE FROM slots WHERE id=?", (sid,))
                        conn.commit()
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def user_section():
    st.title("Bacheca Eventi 🌇")
    
    conn = get_connection()
    slots = conn.execute("SELECT id, data, ora, tema, description FROM slots WHERE is_confirmed=1 ORDER BY data, ora").fetchall()
    conn.close()
    
    if not slots:
        st.warning("Nessun evento disponibile.")
        return

    cols = st.columns(2)
    for idx, s in enumerate(slots):
        sid, s_date, s_time, s_theme, s_desc = s
        
        w_alert = ""
        is_rain, t_max = get_forecast_for_date(s_date)
        if is_rain: w_alert = "⚠️ Pioggia!"
        elif t_max: w_alert = f"☀️ {t_max}°C"
        
        conn = get_connection()
        taken = conn.execute("SELECT count(*) + sum(plus_one) FROM bookings WHERE slot_id=?", (sid,)).fetchone()[0] or 0
        conn.close()
        free = 10 - taken
        
        with cols[idx % 2]:
            with st.container(border=True):
                st.caption(f"{s_date} ore {s_time}")
                st.subheader(s_theme)
                if w_alert: st.caption(w_alert)
                if s_desc: st.caption(f"📝 {s_desc}")
                
                if free > 0:
                    st.success(f"Liberi: {free}/10")
                    
                    with st.expander("🛍️ Spesa"):
                        conn = get_connection()
                        items = conn.execute("SELECT username, item, id FROM bringing WHERE slot_id=?", (sid,)).fetchall()
                        conn.close()
                        if items:
                            for it in items:
                                c_t, c_d = st.columns([4,1])
                                c_t.write(f"{it[0]}: {it[1]}")
                                if it[0] == st.session_state.username:
                                    if c_d.button("x", key=f"rd_{it[2]}"):
                                        conn = get_connection()
                                        conn.execute("DELETE FROM bringing WHERE id=?", (it[2],))
                                        conn.commit()
                                        st.rerun()
                        
                        if st.session_state.username:
                            ni = st.text_input("Porto...", key=f"bi_{sid}")
                            if st.button("Aggiungi", key=f"ba_{sid}"):
                                conn = get_connection()
                                conn.execute("INSERT INTO bringing (slot_id, username, item) VALUES (?, ?, ?)", (sid, st.session_state.username, ni))
                                conn.commit()
                                st.rerun()

                    with st.expander("🎟️ Prenota"):
                        already = is_user_booked(sid, st.session_state.username)
                        if already:
                            st.info("✅ Sei già prenotato! Vai in 'I Miei Eventi' per la chat.")
                        elif not st.session_state.username:
                            st.warning("Accedi per prenotare.")
                        else:
                            with st.form(key=f"book_{sid}"):
                                # Mostra Ruolo nel form
                                role_html = get_user_role_badge(st.session_state.username)
                                st.markdown(f"Prenota come: **{st.session_state.username}** {role_html}", unsafe_allow_html=True)
                                
                                note = st.text_input("Note")
                                p1 = st.checkbox("Porto +1")
                                np1 = ""
                                if p1: np1 = st.text_input("Nome +1")
                                
                                if st.form_submit_button("Conferma"):
                                    needed = 2 if p1 else 1
                                    if free >= needed:
                                        conn = get_connection()
                                        conn.execute("INSERT INTO bookings (slot_id, nome_amico, note, plus_one, nome_plus_one, tieni_status) VALUES (?, ?, ?, ?, ?, 1)", 
                                                     (sid, st.session_state.username, note, 1 if p1 else 0, np1))
                                        conn.commit()
                                        conn.close()
                                        st.snow()
                                        st.success("Prenotato! Vai su 'Le mie Prenotazioni' per la chat.")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("Posti finiti.")
                else:
                    st.error("SOLD OUT")
                    if st.session_state.username:
                        if st.button("Waitlist", key=f"wl_{sid}"):
                            conn = get_connection()
                            conn.execute("INSERT INTO waitlist (slot_id, username) VALUES (?, ?)", (sid, st.session_state.username))
                            conn.commit()
                            st.toast("Sei in lista d'attesa!")

if __name__ == "__main__":
    main()
