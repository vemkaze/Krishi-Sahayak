
import streamlit as st
import speech_recognition as sr
import google.generativeai as genai
from gtts import gTTS
import os
import sounddevice as sd
import numpy as np
import pygame
import time
import tempfile
import threading
from io import BytesIO
import base64
from dotenv import load_dotenv

# Configure the page
st.set_page_config(
    page_title="कृषि सहायक - Krishi Sahayak",
    page_icon="🌾",
    layout="wide"
)


# Load environment variables from .env file
load_dotenv()
# Configure the Gemini API key securely
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False
if 'is_speaking' not in st.session_state:
    st.session_state.is_speaking = False

# Global variables
stop_playback = False
r = sr.Recognizer()

# Pre-defined questions for village farmers (Hinglish/English)
PREDEFINED_QUESTIONS = {
    "Crop Diseases": [
        "Mere wheat ki leaves pe yellow spots aa gaye hai, kya karu?",
        "Rice crop me insects lag gaye hai, treatment batao",
        "Tomato ke plants wilt ho rahe hai, kya problem hai?",
        "Mango tree me fruits gir rahe hai, reason aur solution?"
    ],
    "Fertilizers & Manure": [
        "Wheat ke liye konsa fertilizer best hai?",
        "Rice crop me kab aur kitna urea dalna chahiye?",
        "Organic manure kaise banaye?",
        "Crops ke liye NPK ratio kaise decide kare?"
    ],
    "Weather & Sowing": [
        "Rabi crop kab sow karni chahiye?",
        "Kharif crop ke liye konsa month right hai?",
        "Rain ke baad field preparation kaise kare?",
        "Drought me konsi crop grow kare?"
    ],
    "Animal Husbandry": [
        "Cow ka milk kam ho raha hai, kya kare?",
        "Chickens me disease ke symptoms aur treatment",
        "Buffalo ka fodder kaise prepare kare?",
        "Animals ke liye vaccination kab karana chahiye?"
    ],
    "Horticulture": [
        "Vegetable farming me kya precautions le?",
        "Fruit trees ki care kaise kare?",
        "Chili crop me fruits nahi aa rahe, kya kare?",
        "Onion cultivation ka right method kya hai?"
    ]
}

def create_system_prompt():
    """Create a system prompt for agricultural assistant"""
    return """You are a Krishi Sahayak (Agricultural Assistant) helping Indian farmers. Please follow these guidelines:

1. Answer in simple Hinglish (Hindi + English mix) that farmers understand easily
2. Give practical and actionable advice
3. Consider local Indian farming conditions
4. Use common English farming terms mixed with Hindi
5. Provide solutions along with prevention tips
6. If serious issue, suggest contacting local agricultural expert
7. Be friendly and use farmer-friendly language

Example response style: "Bhai, aapke wheat me yellow spots ka matlab hai ki fungal infection ho sakta hai. Aap copper sulfate spray karo..."

Please respond in this Hinglish style that farmers can easily understand."""

def listen_to_audio():
    """Captures audio from the microphone and transcribes it to text."""
    try:
        print("Listening...")
        # Recording parameters
        samplerate = 16000
        duration = 5  # seconds
        channels = 1

        # Record audio
        audio_data = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=channels, dtype='int16')
        sd.wait()  # Wait until recording is finished

        # Convert to AudioData
        audio = sr.AudioData(audio_data.tobytes(), samplerate, 2)

        print("Recognizing...")
        text = r.recognize_google(audio, language='en-IN')  # English India for better Hinglish support
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        return "Sorry, main aapki baat samajh nahi paya."
    except sr.RequestError as e:
        return f"Google Speech Recognition service me problem: {e}"
    except Exception as e:
        return f"Audio recording me problem: {e}"

def generate_response(prompt):
    """Generates a response using the Gemini API."""
    if not prompt:
        return "Maine aapki baat nahi suni. Please dobara kahiye."
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_prompt = f"{create_system_prompt()}\n\nFarmer ka question: {prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"Error generating response from Gemini: {e}")
        return "Sorry, mujhe AI service se connect karne me problem ho rahi hai."

def text_to_speech(text):
    """Converts text to speech and returns audio data."""
    try:
        tts = gTTS(text=text, lang='en')  # English for better Hinglish support
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tts.save(tmp_file.name)
            return tmp_file.name
    except Exception as e:
        print(f"Error in text-to-speech conversion: {e}")
        return None

def play_audio(audio_file):
    """Play audio file using pygame."""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        os.remove(audio_file)
    except Exception as e:
        print(f"Error playing audio: {e}")

# Main UI
st.title("🌾 Krishi Sahayak - Your Digital Farm Assistant")
st.markdown("### Aapka Digital Agriculture Advisor")

# Sidebar with predefined questions
st.sidebar.title("📋 Common Questions")
st.sidebar.markdown("Neeche diye gaye questions pe click karo:")

selected_question = None
for category, questions in PREDEFINED_QUESTIONS.items():
    st.sidebar.markdown(f"**{category}:**")
    for question in questions:
        if st.sidebar.button(question, key=f"q_{question}"):
            selected_question = question
    st.sidebar.markdown("---")

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 💬 Chat")
    
    # Chat history
    chat_container = st.container()
    with chat_container:
        for i, (user_msg, bot_msg) in enumerate(st.session_state.chat_history):
            st.markdown(f"**👤 You:** {user_msg}")
            st.markdown(f"**🤖 Assistant:** {bot_msg}")
            st.markdown("---")

with col2:
    st.markdown("### 🎤 Voice Input")
    
    # Voice input button
    if st.button("🎤 Speak", disabled=st.session_state.is_listening):
        st.session_state.is_listening = True
        with st.spinner("Listening..."):
            voice_text = listen_to_audio()
            if voice_text and voice_text != "Sorry, main aapki baat samajh nahi paya.":
                response = generate_response(voice_text)
                st.session_state.chat_history.append((voice_text, response))
                
                # Convert response to speech
                audio_file = text_to_speech(response)
                if audio_file:
                    # Play audio in a separate thread
                    threading.Thread(target=play_audio, args=(audio_file,), daemon=True).start()
                
                st.rerun()
        st.session_state.is_listening = False

# Text input
text_input = st.text_input("Ya yaha type karo:", key="text_input")

# Handle predefined question selection
if selected_question:
    text_input = selected_question

# Submit button for text input
if st.button("Send") or text_input:
    if text_input:
        with st.spinner("Answer taiyar kar raha hu..."):
            response = generate_response(text_input)
            st.session_state.chat_history.append((text_input, response))
            
            # Convert response to speech
            audio_file = text_to_speech(response)
            if audio_file:
                # Play audio in a separate thread
                threading.Thread(target=play_audio, args=(audio_file,), daemon=True).start()
            
            st.rerun()

# Clear chat history
if st.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []
    st.rerun()

# Footer
st.markdown("---")
st.markdown("🌾 **Krishi Sahayak** - AI Assistant for Indian Farmers")
st.markdown("💡 **Tip:** Press microphone button aur apna question bolo ya text box me type karo.")

# Instructions
with st.expander("📖 How to Use"):
    st.markdown("""
    **Kaise use kare:**
    1. 🎤 **Voice se:** 'Speak' button press karo aur apna question bolo
    2. ⌨️ **Text se:** Neeche ke box me apna question type karo
    3. 📋 **Ready questions:** Sidebar se koi question choose karo
    
    **Main topics:**
    - Crop diseases aur unka treatment
    - Fertilizer aur manure ki information
    - Weather ke according sowing
    - Animal husbandry advice
    - Horticulture methods
    
    **Example Questions:**
    - "Mere tomato plants me problem hai"
    - "Wheat ke liye best fertilizer konsa hai"
    - "Monsoon me kya crop lagaun"
    """)