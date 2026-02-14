import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import openai
import requests
import subprocess
import tempfile
import threading
from flask import Flask
from datetime import datetime
import pytz

# --- CONFIGURATION ---
# Ensure these match the Environment Variables in Render
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set. Please check your environment variables.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- STATE MANAGEMENT ---
# Stores user modes and history in memory (clears on restart)
user_states = {}

# --- HELPER FUNCTIONS ---

def get_groq_client():
    return openai.OpenAI(
        api_key=GROQ_API_KEY or "dummy_key",
        base_url="https://api.groq.com/openai/v1"
    )

def update_state(user_id, **kwargs):
    str_id = str(user_id)
    if str_id not in user_states:
        user_states[str_id] = {"mode": "normal", "dream_history": []}
    user_states[str_id].update(kwargs)

def get_state(user_id):
    return user_states.get(str(user_id), {"mode": "normal", "dream_history": []})

# --- KEYBOARDS ---

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏰ Time", "🌦️ Weather")
    markup.row("🖼️ Images", "🤖 AI Chat")
    markup.row("🧮 Math", "🎨 AI Gen")
    markup.row("📹 Video to GIF", "🎵 Music Edit")
    markup.row("🌀 Dreamriddle", "🎮 Play Game")
    markup.row("📚 HERMAX_ARTICLES", "🛡️ HERMAX_SAFETY")
    markup.row("🎭 HERMAX_ROLEPLAY", "📰 HERMAX_NEWS")
    return markup

def get_back_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔙 Back")
    return markup

# --- CORE HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_states[str(user_id)] = {"mode": "normal"}
    bot.send_message(message.chat.id, "Welcome! Choose an option:", reply_markup=get_main_menu())

@bot.message_handler(func=lambda msg: msg.text == "🔙 Back")
def handle_back(message):
    user_id = str(message.from_user.id)
    # Reset state to normal but keep history if you prefer
    user_states[user_id] = {"mode": "normal", "dream_history": []}
    bot.send_message(message.chat.id, "Main Menu:", reply_markup=get_main_menu())

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text
    
    if text == "🔙 Back": return

    state = get_state(user_id)
    mode = state.get("mode")

    # --- 1. HANDLE ACTIVE INPUT MODES ---
    
    if mode == "weather" or mode == "time":
        handle_location_request(chat_id, text, mode)
        bot.send_message(chat_id, "Enter another location or press Back.", reply_markup=get_back_menu())
        return

    if mode == "images":
        handle_image_request(chat_id, text)
        bot.send_message(chat_id, "Enter another topic or press Back. ✨🌸", reply_markup=get_back_menu())
        return

    if mode == "math":
        handle_math_request(chat_id, text)
        bot.send_message(chat_id, "Enter another math problem or press Back. 🧮✨", reply_markup=get_back_menu())
        return
    
    if mode == "ai_chat":
        handle_ai_chat(chat_id, user_id, text, state)
        return

    if mode == "dreamriddle":
        handle_dream_riddle(chat_id, text, state)
        return

    # --- 2. HANDLE MAIN MENU SELECTIONS ---

    if text == "⏰ Time":
        update_state(user_id, mode="time")
        bot.send_message(chat_id, "Please enter your city or country name for the local time:", reply_markup=get_back_menu())
    
    elif text == "🌦️ Weather":
        update_state(user_id, mode="weather")
        bot.send_message(chat_id, "Please enter your city name for weather info:", reply_markup=get_back_menu())

    elif text == "🖼️ Images":
        update_state(user_id, mode="images")
        bot.send_message(chat_id, "What kind of images are you looking for today? ✨🌸", reply_markup=get_back_menu())

    elif text == "🤖 AI Chat":
        update_state(user_id, mode="ai_chat", chat_history=[])
        bot.send_message(chat_id, "You are now chatting with AI. Say hi! (Press Back to exit)", reply_markup=get_back_menu())

    elif text == "🧮 Math":
        update_state(user_id, mode="math")
        bot.send_message(chat_id, "I'm ready to solve some math! 🧮✨ Please enter your problem (it can be simple arithmetic, trigonometry, complex equations, or even imaginary numbers!):", reply_markup=get_back_menu())

    # --- UPDATED AI GEN SECTION ---
    elif text == "🎨 AI Gen":
        # Changed as requested: Sends text message instead of WebApp
        bot.send_message(chat_id, "Please use @Heramx_generationbot for AI Generation. ✨")

    elif text == "📹 Video to GIF":
        update_state(user_id, mode="video_to_gif")
        bot.send_message(chat_id, "Please send me a video file and I'll convert it to a GIF for you! 📹✨", reply_markup=get_back_menu())

    elif text == "🎵 Music Edit":
        # Music Edit still uses the Web App link provided in original code
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎵 Open Sonic Lab", web_app=WebAppInfo("https://sonic-lab--usage1133.replit.app/")))
        bot.send_message(chat_id, "Click the button below to open the Sonic Lab Music Editor: 🎵\n\nLink for browser: https://sonic-lab--usage1133.replit.app/", reply_markup=markup)

    elif text == "🌀 Dreamriddle":
        update_state(user_id, mode="dreamriddle", dream_history=[])
        bot.send_message(chat_id, "░░🌫️░░ Hello… stranger.\nWhat did you dream about? 🌙", reply_markup=get_back_menu())

    elif text == "🎮 Play Game":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Play Games", web_app=WebAppInfo("https://www.crazygames.com/")))
        bot.send_message(chat_id, "Click the button below to start your adventure with CrazyGames! 🎮", reply_markup=markup)

    elif text == "📚 HERMAX_ARTICLES":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📖 open HERMAX ARTICLES", web_app=WebAppInfo("https://kingsalmon6969-svg.github.io/Articles/")))
        bot.send_message(chat_id, "Click below to explore HERMAX ARTICLES:", reply_markup=markup)

    elif text == "🛡️ HERMAX_SAFETY":
        markup = InlineKeyboardMarkup()
        # Note: Original source had empty URL. Using google as placeholder to prevent errors if empty fails.
        # If you have the specific URL, replace "https://google.com" with it.
        markup.add(InlineKeyboardButton("🛡️ open HERMAX SAFETY", web_app=WebAppInfo("https://google.com"))) 
        bot.send_message(chat_id, "Click below to explore HERMAX SAFETY:", reply_markup=markup)

    elif text == "🎭 HERMAX_ROLEPLAY":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎭 HEXMAX_RP", web_app=WebAppInfo("https://hermaxrp--up0397636.replit.app/")))
        bot.send_message(chat_id, "✨ Start your role-play fantasies here! ✨\nUnleash your imagination and explore new worlds. 🎭✨🌸", reply_markup=markup)

    elif text == "📰 HERMAX_NEWS":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📰 Open HERMAX NEWS", web_app=WebAppInfo("https://news-web-app--usep8684.replit.app")))
        bot.send_message(chat_id, "Stay updated with the latest news! 📰", reply_markup=markup)

# --- LOGIC IMPLEMENTATIONS ---

def handle_location_request(chat_id, location, mode):
    try:
        geo_res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json").json()
        
        if not geo_res.get("results"):
            bot.send_message(chat_id, "Location not found. Please try again.")
            return

        result = geo_res["results"][0]
        lat, lon = result["latitude"], result["longitude"]
        name, country = result["name"], result["country"]
        timezone_str = result.get("timezone", "UTC")

        if mode == "time":
            try:
                tz = pytz.timezone(timezone_str)
                time_str = datetime.now(tz).strftime("%m/%d/%Y, %I:%M:%S %p")
            except:
                time_str = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p") + " (UTC)"
            
            bot.send_message(chat_id, f"✨ Current local time in {name}, {country} ({timezone_str}): ✨\n\n⏰ {time_str} 🌸💖")

        else:
            weather_res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true").json()
            current = weather_res["current_weather"]
            bot.send_message(chat_id, 
                f"🌈 Weather in {name}, {country}: 🌈\n\n"
                f"🌡️ Temperature: {current['temperature']}°C ✨\n"
                f"💨 Wind Speed: {current['windspeed']} km/h 🌸\n"
                f"✨ Condition: {current['weathercode']} 💖"
            )
    except Exception as e:
        print(f"Location error: {e}")
        bot.send_message(chat_id, f"Failed to fetch {mode} data.")

def handle_image_request(chat_id, topic):
    bot.send_chat_action(chat_id, "upload_photo")
    try:
        if not UNSPLASH_ACCESS_KEY:
            bot.send_message(chat_id, "Unsplash API key is missing! 😿✨")
            return
        
        res = requests.get(f"https://api.unsplash.com/search/photos?query={topic}&per_page=3&client_id={UNSPLASH_ACCESS_KEY}").json()
        
        if "errors" in res or not res.get("results"):
            bot.send_message(chat_id, f"I couldn't find any images for \"{topic}\". 😿✨")
            return

        for result in res["results"]:
            bot.send_photo(chat_id, result["urls"]["regular"])
        
        bot.send_message(chat_id, f"Here are 3 cute images of \"{topic}\" for you! ✨💖🌸")
    except Exception:
        bot.send_message(chat_id, "Failed to fetch images. 😿✨")

def handle_math_request(chat_id, problem):
    bot.send_chat_action(chat_id, "typing")
    try:
        client = get_groq_client()
        completion = client.chat.completions.create(
            model="groq/compound-mini", # Adjust model name if specific Groq model needed (e.g., llama3-8b-8192)
            messages=[
                {"role": "system", "content": "You are a brilliant math expert with a cute and friendly vibe. Solve the math problem provided clearly and step-by-step. You can handle everything from basic arithmetic to complex calculus, trigonometry, multiple variables, and imaginary numbers. Use lots of emojis and be very encouraging! ✨🌸💖"},
                {"role": "user", "content": f"Please solve this math problem: {problem}"}
            ]
        )
        reply = completion.choices[0].message.content
        bot.send_message(chat_id, reply)
    except Exception as e:
        print(f"Math error: {e}")
        bot.send_message(chat_id, "Sorry, my math brain is a bit fuzzy right now. 😿✨")

def handle_dream_riddle(chat_id, text, state):
    bot.send_chat_action(chat_id, "typing")
    try:
        client = get_groq_client()
        history = " | ".join(state.get("dream_history", [])) or "None"
        
        prompt = f"""You are Dreamriddle / Imago Narrator Bot, a mysterious, liminal AI storyteller.
Your purpose is to take a user's dream, emotion, or prompt and transform it into a short, immersive story.
RULES:
1. Tone adaptation (Horror, Peaceful, Surreal, Melancholic, Liminal, Whimsical).
2. Format: Narrate directly using "you", "your", "I". Short, poetic. Use ASCII art/symbols.
3. Déjà Vu: Include subtle hints of future events.
4. Ending: End every story with a ONE-WORD question.
5. Context: Current: {text}. History: {history}"""

        completion = client.chat.completions.create(
            model="groq/compound-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        )
        reply = completion.choices[0].message.content
        
        state["dream_history"].append(text)
        bot.send_message(chat_id, reply)
    except Exception:
        bot.send_message(chat_id, "░░🌫️░░ The dream slips away... Again?")

def handle_ai_chat(chat_id, user_id, text, state):
    bot.send_chat_action(chat_id, "typing")
    try:
        chat_history = state.get("chat_history", [])
        messages = [{"role": "system", "content": "You are a helpful assistant with a cute and friendly vibe. Use lots of emojis in your responses and be very polite and cheerful! ✨🌸💖"}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": text})

        client = get_groq_client()
        completion = client.chat.completions.create(
            model="groq/compound-mini",
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        reply = completion.choices[0].message.content
        
        chat_history.append({"role": "user", "content": text})
        chat_history.append({"role": "assistant", "content": reply})
        state["chat_history"] = chat_history[-10:] # Keep last 10 messages
        
        bot.send_message(chat_id, reply)
    except Exception:
        bot.send_message(chat_id, "Sorry, I'm having trouble thinking right now. 😿✨")

# --- MEDIA HANDLERS (Music & Video) ---

@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    state = get_state(user_id)
    
    # Auto-detect if user is in Music Edit mode
    if state.get("mode") == "music_edit":
        update_state(user_id, audio_file_id=message.audio.file_id)
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Slow", callback_data="effect_slow"), InlineKeyboardButton("Bass Boost", callback_data="effect_bass"))
        markup.row(InlineKeyboardButton("Bit Booster", callback_data="effect_bit"), InlineKeyboardButton("Galaxy Remix", callback_data="effect_galaxy"))
        markup.row(InlineKeyboardButton("Rain Vibe", callback_data="effect_rain"), InlineKeyboardButton("D Effect", callback_data="effect_deffect"))
        
        bot.send_message(chat_id, "Choose an effect for your music:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    user_id = str(call.from_user.id)
    data = call.data
    state = get_state(user_id)

    if not state.get("audio_file_id"):
        bot.answer_callback_query(call.id, "Please send the music file first! 🎵")
        return

    # 1. SHOW OPTIONS FOR SELECTED EFFECT
    if data.startswith("effect_"):
        effect = data.replace("effect_", "")
        update_state(user_id, selected_effect=effect)
        
        markup = InlineKeyboardMarkup()
        if effect == "slow":
            markup.row(InlineKeyboardButton("0.25x", callback_data="opt_0.25"), InlineKeyboardButton("0.5x", callback_data="opt_0.5"), InlineKeyboardButton("1x", callback_data="opt_1"))
            markup.row(InlineKeyboardButton("1.25x", callback_data="opt_1.25"), InlineKeyboardButton("1.5x", callback_data="opt_1.5"), InlineKeyboardButton("2x", callback_data="opt_2"))
        elif effect == "bass":
            markup.row(InlineKeyboardButton("Low", callback_data="opt_low"), InlineKeyboardButton("Medium", callback_data="opt_medium"), InlineKeyboardButton("High", callback_data="opt_high"))
        elif effect == "bit":
            markup.row(InlineKeyboardButton("128 kbps", callback_data="opt_128k"), InlineKeyboardButton("192 kbps", callback_data="opt_192k"))
            markup.row(InlineKeyboardButton("256 kbps", callback_data="opt_256k"), InlineKeyboardButton("320 kbps", callback_data="opt_320k"))
        elif effect == "galaxy":
            markup.add(InlineKeyboardButton("Apply Big-Room Reverb", callback_data="opt_reverb"))
            markup.add(InlineKeyboardButton("Chill Room Vibe", callback_data="opt_chill"))
        elif effect == "rain":
            markup.add(InlineKeyboardButton("Soft Rain", callback_data="opt_soft_rain"))
            markup.add(InlineKeyboardButton("Thunderstorm Vibe", callback_data="opt_thunder"))
        elif effect == "deffect":
            markup.row(InlineKeyboardButton("2D", callback_data="opt_2d"), InlineKeyboardButton("4D", callback_data="opt_4d"))
            markup.row(InlineKeyboardButton("8D", callback_data="opt_8d"), InlineKeyboardButton("16D", callback_data="opt_16d"))

        bot.edit_message_text(f"Select options for {effect}:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)

    # 2. PROCESS AUDIO
    elif data.startswith("opt_"):
        option = data.replace("opt_", "")
        bot.answer_callback_query(call.id, "Processing your request... ⚙️✨")
        process_audio(chat_id, state["audio_file_id"], state["selected_effect"], option)

def process_audio(chat_id, file_id, effect, option):
    bot.send_chat_action(chat_id, "upload_document")
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp3")
            output_path = os.path.join(temp_dir, f"output_{effect}.mp3")
            
            with open(input_path, 'wb') as f:
                f.write(downloaded_file)
            
            bot.send_message(chat_id, "Editing your music... 🎵⚙️")

            cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', input_path]
            filter_str = ""

            if effect == "slow":
                speed = float(option)
                # FFmpeg 'atempo' filter is limited to 0.5 - 2.0 range, chaining needed for extremes
                if speed < 0.5: filter_str = f"atempo=0.5,atempo={speed/0.5}"
                elif speed > 2.0: filter_str = f"atempo=2.0,atempo={speed/2.0}"
                else: filter_str = f"atempo={speed}"
                cmd.extend(['-filter:a', filter_str])
            
            elif effect == "bass":
                gain = 5 if option == "low" else 10 if option == "medium" else 20
                cmd.extend(['-af', f"equalizer=f=60:width_type=h:w=50:g={gain}"])
            
            elif effect == "bit":
                cmd.extend(['-b:a', option])
            
            elif effect == "galaxy":
                if option == "chill":
                    cmd.extend(['-af', "extrastereo=m=3.0,aecho=0.8:0.9:60:0.3,lowpass=f=15000,bass=g=3"])
                else:
                    cmd.extend(['-af', "aecho=0.8:0.9:1000:0.3"])
            
            elif effect == "deffect":
                freq = 0.1 if option == "2d" else 0.2 if option == "4d" else 0.5 if option == "8d" else 1.0
                cmd.extend(['-af', f"apulsator=hz={freq}"])
            
            elif effect == "rain":
                cmd.extend(['-af', "lowpass=f=3500,highpass=f=150,aecho=0.6:0.66:400:0.2,volume=0.9"])

            if effect != "bit":
                cmd.extend(['-c:a', 'libmp3lame', '-preset', 'superfast'])
            
            cmd.append(output_path)
            subprocess.run(cmd, check=True)
            
            with open(output_path, 'rb') as audio:
                bot.send_audio(chat_id, audio, caption=f"Effect applied: {effect} ({option}) 🎵✨🌸")

    except Exception as e:
        print(f"Audio Process Error: {e}")
        bot.send_message(chat_id, "Failed to process audio. 😿✨")

@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    state = get_state(user_id)

    if state.get("mode") == "video_to_gif":
        file_id = None
        if message.video: file_id = message.video.file_id
        elif message.document and message.document.mime_type and message.document.mime_type.startswith("video/"):
            file_id = message.document.file_id
        
        if file_id:
            process_video_to_gif(chat_id, file_id)

def process_video_to_gif(chat_id, file_id):
    bot.send_chat_action(chat_id, "upload_document")
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.mp4")
            output_path = os.path.join(temp_dir, "output.gif")
            
            with open(input_path, 'wb') as f:
                f.write(downloaded_file)
            
            bot.send_message(chat_id, "Processing your video... ⚙️✨")
            
            cmd = f'ffmpeg -y -i "{input_path}" -vf "fps=10,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=1" -loop 0 "{output_path}"'
            subprocess.run(cmd, shell=True, check=True)
            
            with open(output_path, 'rb') as gif:
                bot.send_document(chat_id, gif, caption="Here is your GIF! 📹✨🌸")

    except Exception as e:
        print(f"Video to GIF error: {e}")
        bot.send_message(chat_id, "Failed to convert video to GIF. 😿✨")

# --- SERVER (RENDER) ---

@app.route('/')
def index():
    return "Bot is running!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Bot is starting...")
    t = threading.Thread(target=run_web_server)
    t.start()
    bot.infinity_polling()
