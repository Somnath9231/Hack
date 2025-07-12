import tkinter as tk
from PIL import Image, ImageTk
import os
import threading
import time
import speech_recognition as sr
import requests
from playsound import playsound
import tempfile
from datetime import datetime
import json

# File names
BG_IMAGE = '1.JPG.jpg'
MIC_IMAGE = '2.PNG.png'
BEEP_SOUND_PATH = 'Beep.mp3'
SESSION_LOG = 'session_log.json'

# API Keys
GROQ_API_KEY = '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'
ELEVENLABS_API_KEY = 'sk_af90ba6da907301122b4d11108afe9c1b87c455442e388e9'
VOICE_ID = 'EzHcfR7B0Axr6TgAAU2G'

# Groq settings
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama3-70b-8192'

def detect_emotion(user_text):
    text = user_text.lower()
    emotions = {
        "sad": ["sad", "depressed", "tired", "alone", "exhausted", "hopeless"],
        "angry": ["angry", "mad", "furious", "irritated"],
        "anxious": ["anxious", "nervous", "worried", "panicking", "scared"],
        "happy": ["happy", "glad", "grateful", "excited", "joyful"],
        "lonely": ["lonely", "isolated", "ignored", "abandoned"]
    }
    for emotion, keywords in emotions.items():
        if any(k in text for k in keywords):
            return emotion
    return "neutral"

def log_session(user_text, emotion, file_path=SESSION_LOG):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "text": user_text,
        "emotion": emotion
    }
    try:
        log = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                log = json.load(f)
        log.append(entry)
        with open(file_path, "w") as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        print("❌ Session log error:", e)

def get_last_emotion(file_path=SESSION_LOG):
    try:
        if not os.path.exists(file_path):
            return None, None
        with open(file_path, "r") as f:
            log = json.load(f)
        if log:
            last = log[-1]
            return last["emotion"], last["text"]
        return None, None
    except Exception as e:
        return None, str(e)

class HackApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Psychologist Companion')
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')

        # Background image
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        bg_img = Image.open(BG_IMAGE).resize((screen_width, screen_height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(bg_img)
        tk.Label(self.root, image=self.bg_photo).place(x=0, y=0, relwidth=1, relheight=1)

        # Mic button
        mic_img = Image.open(MIC_IMAGE).resize((80, 80), Image.Resampling.LANCZOS)
        self.mic_photo = ImageTk.PhotoImage(mic_img)
        self.mic_button = tk.Button(self.root, image=self.mic_photo, bd=0, bg='black', command=self.on_mic)
        self.mic_button.place(relx=1.0, rely=1.0, x=-100, y=-100, anchor='se')

        # Exit button
        tk.Button(self.root, text='[X]', font=('Arial', 18, 'bold'), fg='white', bg='red',
                  bd=0, command=self.root.destroy).place(relx=1.0, y=20, x=-40, anchor='ne')

        # Greet with memory
        threading.Thread(target=self.play_startup_greeting).start()

    def play_startup_greeting(self):
        hour = datetime.now().hour
        last_emotion, _ = get_last_emotion()

        if 5 <= hour < 12:
            base = "Morning."
        elif 12 <= hour < 17:
            base = "Hey there."
        elif 17 <= hour < 22:
            base = "Good evening."
        else:
            base = "You're up late."

        if last_emotion == "sad":
            note = "Last time you sounded a bit low. Want to talk about it?"
        elif last_emotion == "anxious":
            note = "You seemed a little anxious earlier. How are things now?"
        elif last_emotion == "happy":
            note = "Last time you sounded happy. Hope you’re still feeling good."
        elif last_emotion == "angry":
            note = "You sounded frustrated earlier. Want to unpack that?"
        elif last_emotion == "lonely":
            note = "You mentioned feeling lonely last time. I'm still here for you."
        elif last_emotion:
            note = f"Last time we talked, you mentioned feeling {last_emotion}."
        else:
            note = "I'm glad you're here. Just say what's on your mind."

        self.speak_with_elevenlabs(f"{base} {note}")

    def on_mic(self):
        threading.Thread(target=self.listen_and_respond).start()

    def listen_and_respond(self):
        try:
            if os.path.exists(BEEP_SOUND_PATH):
                playsound(BEEP_SOUND_PATH)

            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("🎤 Listening...")
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                print("🧠 Transcribing...")
                text = r.recognize_google(audio)
                print("📢 You said:", text)

                if text.strip():
                    emotion = detect_emotion(text)
                    log_session(text, emotion)
                    reply = self.get_groq_response(text)
                    if reply:
                        self.speak_with_elevenlabs(reply)
        except sr.WaitTimeoutError:
            print("❌ Timeout: No speech detected.")
        except sr.UnknownValueError:
            print("❌ Speech not recognized.")
        except Exception as e:
            print("❌ Listening error:", e)

    def get_groq_response(self, user_input):
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = (
            "You are a real human psychologist. Speak like a friend who deeply understands emotions. "
            "Keep answers short, natural, and realistic. Avoid robotic phrases or giving fake praise. "
            "Ask thoughtful follow-up questions. Do not say you're an AI or assistant."
        )

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ]
        }

        try:
            response = requests.post(GROQ_URL, json=payload, headers=headers)
            print("🔍 Groq Response:", response.status_code, response.text)

            data = response.json()
            if 'choices' in data:
                return data['choices'][0]['message']['content']
            return "Hmm, I’m not sure I understood that. Want to try again?"
        except Exception as e:
            print("❌ Groq API error:", e)
            return "Something went wrong. But I'm still listening."

    def speak_with_elevenlabs(self, text):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            print("🎙️ ElevenLabs Status:", response.status_code)

            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    fp.write(response.content)
                    fp.close()
                    playsound(fp.name)
                    os.remove(fp.name)
            else:
                print("❌ ElevenLabs Error:", response.status_code)
        except Exception as e:
            print("❌ ElevenLabs error:", e)

if __name__ == '__main__':
    root = tk.Tk()
    app = HackApp(root)
    root.mainloop()
