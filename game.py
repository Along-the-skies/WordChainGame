import json
import random
import threading
import time
import paho.mqtt.client as mqtt
from english_words import get_english_words_set
from tkinter import messagebox

#======================================================
#============Variables=================================
#=======================================================

BROKER = 'test.mosquitto.org'
PORT = 1883
RoomId= ""
VALIDWORDS = get_english_words_set(['web2'], lower=True)
PlayerName = ""
players = []
scores = {}
strikes = {}
RequiredLetter = ""
CurrentTurn = ""
timer = 0

UsedWords = set()
mqtt_client = None
game_active = False
waiting_for_player = False
room_full = False
ui_active = False
received_state = False
max_players = 2
strike_limit = 3

BG = "#081C15"
CARD = "#1B4332"
CARD2 = "#25503E"
ACCENT = "#52B788"
HIGHLIGHT = "#95D5B2"
WOOD = "#5C4033"
TEXT = "#F1FAEE"
RED = "#D62828"

#====================================================
#===============Some Functions======================
#====================================================

def isValidWord(word):
    word=word.lower()
    return word in VALIDWORDS


#===========Game Logic Functions==================


def reset_local_state():
    global players, scores, strikes, CurrentTurn, RequiredLetter, timer, UsedWords
    global game_active, waiting_for_player, room_full, received_state

    players.clear()
    scores.clear()
    strikes.clear()
    CurrentTurn = ""
    RequiredLetter = ""
    timer = 0
    UsedWords.clear()
    game_active = False
    waiting_for_player = False
    room_full = False
    received_state = False


def validateSubmissions(playerName, word):
    global RequiredLetter, UsedWords, CurrentTurn, timer, scores, strikes, game_active

    if not game_active:
        return

    word = word.lower()
    scores.setdefault(playerName, 0)
    strikes.setdefault(playerName, 0)

    if playerName != CurrentTurn:
        strikes[playerName] += 1
        if strikes[playerName] > strike_limit:
            EliminatePlayer(playerName)
        PublishGameState()
        return

    if not isValidWord(word):
        strikes[playerName] += 1
        if strikes[playerName] > strike_limit:
            EliminatePlayer(playerName)
        PublishGameState()
        return

    if word in UsedWords:
        strikes[playerName] += 1
        if strikes[playerName] > strike_limit:
            EliminatePlayer(playerName)
        PublishGameState()
        return

    if word[0] != RequiredLetter.lower():
        strikes[playerName] += 1
        if strikes[playerName] > strike_limit:
            EliminatePlayer(playerName)
        PublishGameState()
        return

    UsedWords.add(word)
    RequiredLetter = word[-1].upper()
    scores[playerName] += 1
    nextTurn()
    PublishGameState()


def nextTurn():
    global CurrentTurn, players, timer

    if len(players) != max_players:
        return

    if CurrentTurn == players[0]:
        CurrentTurn = players[1]
    elif CurrentTurn == players[1]:
        CurrentTurn = players[0]

    timer = 30


def EliminatePlayer(playerName):
    global players, scores, strikes, game_active

    if playerName not in players:
        return

    players.remove(playerName)
    scores.pop(playerName, None)
    strikes.pop(playerName, None)

    if len(players) == 1:
        game_active = False
        PublishWinner(players[0])
    elif len(players) == 0:
        reset_local_state()


def StartGame():
    global players, CurrentTurn, RequiredLetter, timer, scores, strikes, UsedWords, game_active, waiting_for_player

    if len(players) != max_players:
        return

    seed_value = sum(ord(c) for c in RoomId + ''.join(sorted(players)))
    rng = random.Random(seed_value)
    CurrentTurn = rng.choice(players)
    RequiredLetter = rng.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    timer = 30
    scores = {player: 0 for player in players}
    strikes = {player: 0 for player in players}
    UsedWords.clear()
    game_active = True
    waiting_for_player = False
    PublishGameState()


def EndGame():
    global players

    if len(players) == 1:
        PublishWinner(players[0])

    reset_local_state()


def ShowWinner(winner):
    messagebox.showinfo("Game Over", f"Winner: {winner}")
    if mqtt_client is not None:
        try:
            mqtt_client.disconnect()
        except Exception:
            pass
    reset_local_state()
    show_login_screen()


#==============MQTT Functions===================

def connectMQTT():
    global mqtt_client

    if mqtt_client is not None:
        return

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.loop_start()


def on_connect(client, userdata, flags, rc):
    client.subscribe(f"wordchain/{RoomId}/join")
    client.subscribe(f"wordchain/{RoomId}/leave")
    client.subscribe(f"wordchain/{RoomId}/word")
    client.subscribe(f"wordchain/{RoomId}/state")
    client.subscribe(f"wordchain/{RoomId}/winner")


def on_message(client, userdata, msg):
    global players, scores, strikes, CurrentTurn, RequiredLetter, timer, UsedWords
    global waiting_for_player, room_full, game_active, received_state

    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        return

    topic = msg.topic

    if topic == f"wordchain/{RoomId}/join":
        player = data.get("player")
        if not player:
            return

        if player in players:
            return

        if len(players) >= max_players:
            if player == PlayerName:
                room_full = True
                if mqtt_client:
                    mqtt_client.disconnect()
                reset_local_state()
            return

        players.append(player)
        scores.setdefault(player, 0)
        strikes.setdefault(player, 0)

        if len(players) == max_players:
            waiting_for_player = False
            if not game_active:
                StartGame()
        else:
            PublishGameState()

        if root.winfo_exists():
            root.after(0, updateUI)

    elif topic == f"wordchain/{RoomId}/leave":
        player = data.get("player")
        if player in players:
            players.remove(player)
            scores.pop(player, None)
            strikes.pop(player, None)

        if game_active and len(players) == 1:
            game_active = False
            PublishWinner(players[0])
        elif len(players) == 0:
            reset_local_state()
        else:
            PublishGameState()

    elif topic == f"wordchain/{RoomId}/word":
        validateSubmissions(data.get("player", ""), data.get("word", ""))

    elif topic == f"wordchain/{RoomId}/state":
        players = data.get("players", [])
        CurrentTurn = data.get("turn", "")
        RequiredLetter = data.get("required", "")
        timer = data.get("timer", 0)
        UsedWords = set(data.get("used", []))
        scores = data.get("scores", {player: 0 for player in players})
        strikes = data.get("strikes", {player: 0 for player in players})
        game_active = len(players) == max_players and CurrentTurn != ""
        waiting_for_player = len(players) == 1 and not game_active
        received_state = True

        if len(players) == max_players and PlayerName not in players:
            room_full = True
            if mqtt_client:
                try:
                    mqtt_client.disconnect()
                    mqtt_client.loop_stop()
                except Exception:
                    pass
            reset_local_state()
            if root.winfo_exists():
                root.after(0, show_login_screen)
        if root.winfo_exists():
            root.after(0, updateUI)

    elif topic == f"wordchain/{RoomId}/winner":
        winner = data.get("winner")
        if winner:
            if root.winfo_exists():
                root.after(0, lambda: ShowWinner(winner))
            if mqtt_client:
                try:
                    mqtt_client.disconnect()
                    mqtt_client.loop_stop()
                except Exception:
                    pass
            reset_local_state()


def PublishGameState():
    if mqtt_client is None:
        return

    data = {
        "players": players,
        "scores": scores,
        "strikes": strikes,
        "turn": CurrentTurn,
        "required": RequiredLetter,
        "timer": timer,
        "used": list(UsedWords)
    }

    mqtt_client.publish(
        f"wordchain/{RoomId}/state",
        json.dumps(data)
    )


def PublishWinner(winner):
    if mqtt_client is None:
        return

    mqtt_client.publish(
        f"wordchain/{RoomId}/winner",
        json.dumps({"winner": winner})
    )


def SendWord(word):
    if mqtt_client is None:
        return

    data = {
        "player": PlayerName,
        "word": word
    }

    mqtt_client.publish(
        f"wordchain/{RoomId}/word",
        json.dumps(data)
    )


def Join_room():
    global players, scores, strikes, waiting_for_player

    if mqtt_client is None:
        connectMQTT()

    if room_full:
        return

    if PlayerName and PlayerName not in players:
        players.append(PlayerName)
        scores.setdefault(PlayerName, 0)
        strikes.setdefault(PlayerName, 0)
        waiting_for_player = len(players) < max_players
        updateUI()

    data = {"player": PlayerName}
    mqtt_client.publish(
        f"wordchain/{RoomId}/join",
        json.dumps(data)
    )


def show_login_screen():
    global ui_active

    ui_active = False
    loginFrame.pack(fill="x", padx=20, pady=10)
    mainFrame.pack_forget()
    inputCard.pack_forget()
    bottomCard.pack_forget()


def Leave_Room():
    global mqtt_client

    if mqtt_client is not None:
        data = {"player": PlayerName}
        mqtt_client.publish(
            f"wordchain/{RoomId}/leave",
            json.dumps(data)
        )

        if mqtt_client is not None:
            try:
                mqtt_client.publish(
                    f"wordchain/{RoomId}/state",
                    json.dumps({
                        "players": [],
                        "scores": {},
                        "strikes": {},
                        "turn": "",
                        "required": "",
                        "timer": 0,
                        "used": []
                    })
                )
            except Exception:
                pass

        try:
            mqtt_client.disconnect()
            mqtt_client.loop_stop()
        except Exception:
            pass
        mqtt_client = None

    reset_local_state()
    show_login_screen()

#==========GUI FUNCTIONS================

def submitPressed():
    word = wordEntry.get().strip()
    if not word:
        return

    if mqtt_client is None:
        messagebox.showwarning("Not connected", "Please set RoomId and PlayerName and reconnect before submitting.")
        return

    SendWord(word)
    wordEntry.delete(0, "end")


def updateUI():
    if not ui_active or not root.winfo_exists():
        return

    roomLabel.configure(text=f"ROOM: {RoomId or '---'}")

    if room_full:
        statusText = "Room Full"
    elif waiting_for_player:
        statusText = "Waiting for another player..."
    elif not game_active:
        statusText = "Waiting for game to start..."
    else:
        statusText = ""

    statusLabel.configure(text=statusText)
    turnLabel.configure(text=CurrentTurn or "---")
    letterLabel.configure(text=RequiredLetter or "-")
    timerLabel.configure(text=f"00:{timer:02d}" if timer else "00:00")

    strikes_count = strikes.get(PlayerName, 0)
    strike_text = " ".join("❌" if i < strikes_count else "●" for i in range(strike_limit))
    strikeLabel.configure(text=strike_text)

    for widget in playersListFrame.winfo_children():
        widget.destroy()

    if not players:
        emptyLabel = ctk.CTkLabel(
            playersListFrame,
            text="No players yet",
            font=("Arial", 12),
            text_color=TEXT
        )
        emptyLabel.pack(fill="x", pady=2)
    else:
        for player in players:
            playerFrame = ctk.CTkFrame(
                playersListFrame,
                fg_color=CARD2,
                corner_radius=10
            )
            playerFrame.pack(fill="x", pady=3)

            ctk.CTkLabel(
                playerFrame,
                text=f"🟢 {player}",
                font=("Arial", 13, "bold"),
                text_color=TEXT
            ).pack(side="left", padx=10, pady=8)

            ctk.CTkLabel(
                playerFrame,
                text=str(scores.get(player, 0)),
                font=("Arial", 16, "bold"),
                text_color=HIGHLIGHT
            ).pack(side="right", padx=10)

    for widget in usedWords.winfo_children():
        widget.destroy()

    if not UsedWords:
        emptyLabel = ctk.CTkLabel(
            usedWords,
            text="No used words yet",
            anchor="w",
            font=("Arial", 12),
            text_color=TEXT
        )
        emptyLabel.pack(fill="x", padx=5, pady=2)
    else:
        for word in sorted(UsedWords):
            ctk.CTkLabel(
                usedWords,
                text=word,
                anchor="w",
                font=("Arial", 12),
                text_color=TEXT
            ).pack(fill="x", padx=5, pady=2)


def generate_room_id():
    global RoomId
    new_id = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(6))
    RoomId = new_id
    loginRoomEntry.delete(0, "end")
    loginRoomEntry.insert(0, new_id)


def start_game_session():
    global PlayerName, RoomId, BROKER, ui_active

    name = loginNameEntry.get().strip()
    room = loginRoomEntry.get().strip().upper()
    server = serverComboBox.get().strip()

    if not name:
        messagebox.showwarning("Missing name", "Please enter a player name.")
        return

    if not room or len(room) != 6:
        messagebox.showwarning("Invalid room", "Please enter a valid 6-letter room ID.")
        return

    PlayerName = name
    RoomId = room
    BROKER = server or BROKER

    ui_active = True
    loginFrame.pack_forget()
    mainFrame.pack(fill="both", expand=True, padx=10, pady=5)
    inputCard.pack(
        fill="x",
        padx=10,
        pady=(0, 5)
    )
    bottomCard.pack(
        fill="x",
        padx=10,
        pady=(0, 10)
    )
    updateUI()
    updateTimer()
    connectMQTT()
    Join_room()


def updateTimer():
    global timer

    if game_active and timer > 0:
        timer -= 1
    updateUI()
    root.after(1000, updateTimer)


#=====================================
#============GUI CODE=================
#=====================================

import customtkinter as ctk

# ========================
# Window
# ========================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

root = ctk.CTk()
root.title("Word Chain Multiplayer")
root.geometry("600x500")
root.resizable(False, False)

# ========================
# Colors
# ========================



root.configure(fg_color=BG)

# ========================
# Title
# ========================

titleLabel = ctk.CTkLabel(
    root,
    text="🌿 WORD CHAIN Multiplayer",
    font=("Arial", 22, "bold"),
    text_color=HIGHLIGHT
)
titleLabel.pack(pady=(8, 5))

# ========================
# Main Area
# ========================

mainFrame = ctk.CTkFrame(
    root,
    fg_color="transparent"
)

# ========================
# Login Card
# ========================

loginFrame = ctk.CTkFrame(
    root,
    fg_color=CARD,
    corner_radius=15
)
loginFrame.pack(fill="x", padx=20, pady=10)

loginTitle = ctk.CTkLabel(
    loginFrame,
    text="JOIN ROOM",
    font=("Arial", 18, "bold"),
    text_color=HIGHLIGHT
)
loginTitle.pack(pady=(12, 8))

loginNameLabel = ctk.CTkLabel(
    loginFrame,
    text="Player Name",
    font=("Arial", 12, "bold"),
    text_color=TEXT
)
loginNameLabel.pack(anchor="w", padx=15, pady=(0, 4))

loginNameEntry = ctk.CTkEntry(
    loginFrame,
    placeholder_text="Enter player name",
    height=38,
    font=("Arial", 14),
    corner_radius=10
)
loginNameEntry.pack(fill="x", padx=15, pady=(0, 10))

loginRoomLabel = ctk.CTkLabel(
    loginFrame,
    text="Room UID",
    font=("Arial", 12, "bold"),
    text_color=TEXT
)
loginRoomLabel.pack(anchor="w", padx=15, pady=(0, 4))

roomRow = ctk.CTkFrame(loginFrame, fg_color="transparent")
roomRow.pack(fill="x", padx=15, pady=(0, 10))

loginRoomEntry = ctk.CTkEntry(
    roomRow,
    placeholder_text="6-letter room id",
    height=38,
    font=("Arial", 14),
    corner_radius=10
)
loginRoomEntry.pack(side="left", fill="x", expand=True)

generateRoomButton = ctk.CTkButton(
    roomRow,
    text="GENERATE",
    width=120,
    height=38,
    font=("Arial", 12, "bold"),
    fg_color=ACCENT,
    hover_color="#40916C",
    command=lambda: generate_room_id()
)
generateRoomButton.pack(side="left", padx=(10, 0))

serverLabel = ctk.CTkLabel(
    loginFrame,
    text="Server",
    font=("Arial", 12, "bold"),
    text_color=TEXT
)
serverLabel.pack(anchor="w", padx=15, pady=(0, 4))

serverVar = ctk.StringVar(value="test.mosquitto.org")
serverComboBox = ctk.CTkComboBox(
    loginFrame,
    values=["test.mosquitto.org"],
    variable=serverVar,
    font=("Arial", 14),
    button_color=CARD2,
    fg_color=CARD2,
    text_color=TEXT,
    dropdown_fg_color=WOOD,
    dropdown_text_color=TEXT
)
serverComboBox.pack(fill="x", padx=15, pady=(0, 10))

playButton = ctk.CTkButton(
    loginFrame,
    text="PLAY",
    width=200,
    height=44,
    font=("Arial", 14, "bold"),
    fg_color=ACCENT,
    hover_color="#40916C",
    command=lambda: start_game_session()
)
playButton.pack(pady=(4, 16))

# ========================
# Left Column
# ========================

leftFrame = ctk.CTkFrame(
    mainFrame,
    fg_color="transparent"
)
leftFrame.pack(
    side="left",
    fill="y",
    expand=True,
    padx=(0, 5)
)

# ========================
# Players Card
# ========================

playersCard = ctk.CTkFrame(
    leftFrame,
    fg_color=CARD,
    corner_radius=15
)
playersCard.pack(
    fill="x",
    pady=(0, 5)
)

playersTitle = ctk.CTkLabel(
    playersCard,
    text="PLAYERS",
    font=("Arial", 15, "bold"),
    text_color=ACCENT
)
playersTitle.pack(pady=(8, 5))

playersListFrame = ctk.CTkFrame(
    playersCard,
    fg_color="transparent"
)
playersListFrame.pack(
    fill="x",
    padx=8,
    pady=(0, 5)
)

# ========================
# Used Words Card
# ========================

usedCard = ctk.CTkFrame(
    leftFrame,
    fg_color=CARD,
    corner_radius=15,
    height=180
)

usedCard.pack(
    fill="x",
    pady=(0, 5)
)

usedCard.pack_propagate(False)

usedTitle = ctk.CTkLabel(
    usedCard,
    text="USED WORDS",
    font=("Arial", 15, "bold"),
    text_color=ACCENT
)
usedTitle.pack(
    pady=(8, 5)
)

usedWords = ctk.CTkScrollableFrame(
    usedCard,
    fg_color=CARD2,
    corner_radius=10,
    height=120
)

usedWords.pack(
    fill="both",
    expand=True,
    padx=8,
    pady=(0, 8)
)

# ========================
# Right Column
# ========================

rightFrame = ctk.CTkFrame(
    mainFrame,
    fg_color="transparent"
)

rightFrame.pack(
    side="right",
    fill="both",
    expand=True,
    padx=(5, 0)
)

# ========================
# Turn Card
# ========================

turnCard = ctk.CTkFrame(
    rightFrame,
    fg_color=WOOD,
    corner_radius=15
)

turnCard.pack(
    fill="x",
    pady=(0, 5)
)

turnTitle = ctk.CTkLabel(
    turnCard,
    text="CURRENT TURN",
    font=("Arial", 15, "bold"),
    text_color=TEXT
)

turnLabel = ctk.CTkLabel(
    turnCard,
    text="Bob",
    font=("Arial", 26, "bold"),
    text_color=HIGHLIGHT
)

timerLabel = ctk.CTkLabel(
    turnCard,
    text="00:25",
    font=("Arial", 13),
    text_color=TEXT
)

turnTitle.pack(pady=(10, 2))
turnLabel.pack()
timerLabel.pack(pady=(0, 10))

# ========================
# Required Letter Card
# ========================

letterCard = ctk.CTkFrame(
    rightFrame,
    fg_color=CARD,
    corner_radius=15
)

letterCard.pack(
    fill="both",
    expand=True
)

letterTitle = ctk.CTkLabel(
    letterCard,
    text="REQUIRED LETTER",
    font=("Arial", 15, "bold"),
    text_color=ACCENT
)

letterLabel = ctk.CTkLabel(
    letterCard,
    text="T",
    font=("Arial", 70, "bold"),
    text_color=HIGHLIGHT
)

letterTitle.pack(
    pady=(15, 5)
)

letterLabel.pack(
    expand=True
)

# ========================
# Input Area
# ========================

inputCard = ctk.CTkFrame(
    root,
    fg_color=CARD,
    corner_radius=15
)

wordEntry = ctk.CTkEntry(
    inputCard,
    placeholder_text="Enter word...",
    height=38,
    font=("Arial", 14),
    corner_radius=10
)

wordEntry.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(10, 5),
    pady=8
)
wordEntry.bind("<Return>", lambda event: submitPressed())

submitButton = ctk.CTkButton(
    inputCard,
    text="SUBMIT",
    width=100,
    height=38,
    font=("Arial", 14, "bold"),
    fg_color=ACCENT,
    hover_color="#40916C",
    text_color="black",
    corner_radius=10,
    command=submitPressed
)

submitButton.pack(
    side="right",
    padx=(0, 10),
    pady=8
)

# ========================
# Bottom Bar
# ========================

bottomCard = ctk.CTkFrame(
    root,
    fg_color=CARD,
    corner_radius=15
)

strikeLabel = ctk.CTkLabel(
    bottomCard,
    text="❌ ● ●",
    font=("Arial", 16),
    text_color=RED
)

strikeLabel.pack(
    side="left",
    padx=10,
    pady=8
)

roomLabel = ctk.CTkLabel(
    bottomCard,
    text="ROOM: ABCD12",
    font=("Arial", 12, "bold"),
    text_color=TEXT
)

roomLabel.pack(
    side="left",
    expand=True
)

statusLabel = ctk.CTkLabel(
    bottomCard,
    text="",
    font=("Arial", 12, "bold"),
    text_color=ACCENT
)
statusLabel.pack(
    side="left",
    padx=10,
    pady=8
)

leaveButton = ctk.CTkButton(
    bottomCard,
    text="LEAVE",
    width=100,
    height=34,
    fg_color=RED,
    hover_color="#B51717",
    corner_radius=10,
    font=("Arial", 12, "bold"),
    command=Leave_Room
)

leaveButton.pack(
    side="right",
    padx=10,
    pady=8
)

# ========================
# Main Loop
# ========================

root.mainloop()