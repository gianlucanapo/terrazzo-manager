import random
import streamlit as st


RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]


def new_deck():
    """Create and shuffle a fresh 52-card deck."""
    deck = [(rank, suit) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def draw_card():
    """Draw a card from the deck, reloading a fresh deck if empty."""
    if not st.session_state.deck:
        st.session_state.deck = new_deck()
    return st.session_state.deck.pop()


def card_label(card):
    """Format a card for display."""
    rank, suit = card
    return f"{rank}{suit}"


def hand_value(hand):
    """Calculate the hand value, treating aces as 1 or 11."""
    total = 0
    aces = 0
    for rank, _ in hand:
        if rank in {"J", "Q", "K"}:
            total += 10
        elif rank == "A":
            total += 11
            aces += 1
        else:
            total += int(rank)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def init_state():
    """Initialize session state once."""
    if "deck" not in st.session_state:
        st.session_state.deck = []
    if "player_hand" not in st.session_state:
        st.session_state.player_hand = []
    if "dealer_hand" not in st.session_state:
        st.session_state.dealer_hand = []
    if "phase" not in st.session_state:
        st.session_state.phase = "idle"
    if "message" not in st.session_state:
        st.session_state.message = ""


def start_new_hand():
    """Reset the round and deal two cards each."""
    st.session_state.deck = new_deck()
    st.session_state.player_hand = [draw_card(), draw_card()]
    st.session_state.dealer_hand = [draw_card(), draw_card()]
    st.session_state.phase = "player_turn"
    st.session_state.message = "Nuova mano: tocca a te."


def dealer_play():
    """Dealer draws until reaching at least 17."""
    while hand_value(st.session_state.dealer_hand) < 17:
        st.session_state.dealer_hand.append(draw_card())


def resolve_round():
    """Determine the outcome and set the message."""
    player_total = hand_value(st.session_state.player_hand)
    dealer_total = hand_value(st.session_state.dealer_hand)

    if player_total > 21:
        st.session_state.message = "Hai sballato. Vince il banco."
        return
    if dealer_total > 21:
        st.session_state.message = "Il banco sballa. Hai vinto!"
        return
    if player_total > dealer_total:
        st.session_state.message = "Hai vinto!"
        return
    if player_total < dealer_total:
        st.session_state.message = "Vince il banco."
        return
    st.session_state.message = "Pareggio."


init_state()

st.title("Blackjack")
st.write("Gioca una mano con un solo mazzo. A vale 1 o 11, J/Q/K valgono 10.")

col_new, col_hit, col_stand = st.columns(3)

with col_new:
    if st.button("Nuova mano"):
        start_new_hand()

with col_hit:
    if st.button("Carta", disabled=st.session_state.phase != "player_turn"):
        st.session_state.player_hand.append(draw_card())
        if hand_value(st.session_state.player_hand) > 21:
            st.session_state.phase = "round_over"
            resolve_round()

with col_stand:
    if st.button("Stai", disabled=st.session_state.phase != "player_turn"):
        st.session_state.phase = "dealer_turn"
        dealer_play()
        st.session_state.phase = "round_over"
        resolve_round()

st.divider()

st.subheader("Banco")
if st.session_state.dealer_hand:
    if st.session_state.phase == "player_turn":
        visible = ["🂠"]
        if len(st.session_state.dealer_hand) > 1:
            visible.append(card_label(st.session_state.dealer_hand[1]))
        st.write(" ".join(visible))
        st.caption("Valore: ?")
    else:
        st.write(" ".join(card_label(card) for card in st.session_state.dealer_hand))
        st.caption(f"Valore: {hand_value(st.session_state.dealer_hand)}")
else:
    st.write("Nessuna carta.")

st.subheader("Giocatore")
if st.session_state.player_hand:
    st.write(" ".join(card_label(card) for card in st.session_state.player_hand))
    st.caption(f"Valore: {hand_value(st.session_state.player_hand)}")
else:
    st.write("Nessuna carta.")

if st.session_state.message:
    st.info(st.session_state.message)
