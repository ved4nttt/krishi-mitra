import os
import re
import uuid
import base64
import psycopg2
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from deep_translator import GoogleTranslator
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
import uvicorn

app = FastAPI(title="Krishi-Mitra Production Engine")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== CONFIGURATION & SECRETS ====================

DB_URL = os.getenv("DB_URL")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER", "whatsapp:+14155238886")  
BASE_URL = os.getenv("BASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# ==================== DATABASE INITIALIZATION & MIGRATION ====================
def get_db():
    return psycopg2.connect(DB_URL)

@app.on_event("startup")
def startup_event():
    """Auto-migrates the database to include the new 'location' column if missing."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT location FROM users LIMIT 1")
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        cursor.execute("ALTER TABLE users ADD COLUMN location VARCHAR(255) DEFAULT 'PENDING'")
        conn.commit()
        print("✅ Database Auto-Migrated: 'location' column added to users table.")
    except Exception as e:
        print(f"DB Check Error: {e}")
    finally:
        cursor.close()
        conn.close()

# ==================== HELPER ENGINES & PROMPTS ====================
MANDI_DATABASE = {
    "wheat": "₹2,450 - ₹2,620 per quintal", "gehu": "₹2,450 - ₹2,620 per quintal", "kanak": "₹2,450 - ₹2,620 per quintal",
    "paddy": "₹2,200 - ₹2,400 per quintal", "jhona": "₹2,200 - ₹2,400 per quintal", "rice": "₹2,200 - ₹2,400 per quintal",
    "cotton": "₹7,100 - ₹7,650 per quintal", "kapas": "₹7,100 - ₹7,650 per quintal", "narma": "₹7,100 - ₹7,650 per quintal",
    "mustard": "₹5,300 - ₹5,750 per quintal", "sarson": "₹5,300 - ₹5,750 per quintal",
    "onion": "₹1,800 - ₹2,350 per quintal", "pyaz": "₹1,800 - ₹2,350 per quintal", "kanda": "₹1,800 - ₹2,350 per quintal",
    "soybean": "₹4,200 - ₹4,650 per quintal", "potato": "₹1,400 - ₹1,750 per quintal", "aloo": "₹1,400 - ₹1,750 per quintal",
    "kinnow": "₹2,000 - ₹2,500 per quintal", "sugarcane": "₹315 - ₹340 per quintal", "ganna": "₹315 - ₹340 per quintal",
}

GREETINGS = ["hi", "hello", "hey", "namaste", "sat sri akal", "menu", "help", "start", "नमस्कार", "नमस्ते", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "hii"]
CHANGE_LOC_KEYWORDS = ["change location", "update location", "location badlo", "लोकेशन बदलें", "जगह बदलें", "स्थान बदलें", "ठिकाण बदला", "लोकेशन बदला", "location badal", "ਲੋਕੇਸ਼ਨ ਬਦਲੋ", "ਜਗ੍ਹਾ ਬਦਲੋ"]

def get_full_manual(lang_code: str) -> str:
    manuals = {
        "1": "📖 *Krishi-Mitra User Manual* 📖\n\nHere is everything I can do to help your farm:\n📍 *Weather:* Ask for weather updates or send a GPS Pin for local rain forecasts.\n📸 *Crop Doctor:* Send a photo of a sick plant for an instant AI disease diagnosis!\n🌱 *Mandi Rates:* Ask for crop prices (e.g., 'Wheat price today').\n🤖 *Farming Advice:* Ask any question about fertilizers, pests, or PM-Kisan schemes.\n🎙️ *Voice Mode:* Send a voice note, or just add the word *'voice'* to your text to hear me speak!\n\n*(⚙️ Settings: Type 'Change location' or text 1, 2, 3, 4 anytime to change language)*",
        "2": "📖 *कृषि-मित्र यूजर मैनुअल* 📖\n\nयहाँ बताया गया है कि मैं आपकी कैसे मदद कर सकता हूँ:\n📍 *मौसम:* मौसम का हाल पूछें या लाइव लोकेशन पिन भेजें।\n📸 *फसल डॉक्टर:* बीमार पौधे की फोटो भेजकर तुरंत इलाज पाएं!\n🌱 *मंडी भाव:* ताज़ा रेट जानें (जैसे 'गेहूं का भाव')।\n🤖 *सलाह:* खाद, कीटनाशक, या पीएम-किसान के बारे में पूछें।\n🎙️ *वॉइस मोड:* बोलकर जवाब सुनने के लिए वॉइस नोट भेजें या अपने सवाल में 'voice' लिखें!\n\n*(⚙️ सेटिंग: जगह बदलने के लिए 'Change location' लिखें या भाषा बदलने के लिए 1, 2, 3, 4 दबाएं)*",
        "3": "📖 *कृषी-मित्र वापरकर्ता मॅन्युअल* 📖\n\nमी शेतीसाठी कशी मदत करू शकतो ते येथे आहे:\n📍 *हवामान:* हवामान विचारा किंवा तुमची लोकेशन पिन पाठवा.\n📸 *पीक डॉक्टर:* आजारी पिकाचा फोटो पाठवा आणि त्वरित निदान मिळवा!\n🌱 *बाजारभाव:* पिकांचे ताजे भाव विचारा.\n🤖 *सल्ला:* खते, रोग नियंत्रण किंवा पीएम-किसान योजनांची माहिती.\n🎙️ *ऑडिओ मोड:* ऑडिओ उत्तर मिळवण्यासाठी व्हॉइस नोट पाठवा किंवा 'voice' लिहा!\n\n*(⚙️ सेटिंग्ज: ठिकाण बदलण्यासाठी 'Change location' लिहा किंवा भाषा बदलण्यासाठी कधीही 1, 2, 3, 4 पाठवा)*",
        "4": "📖 *ਕ੍ਰਿਸ਼ੀ-ਮਿੱਤਰ ਯੂਜ਼ਰ ਮੈਨੂਅਲ* 📖\n\nਮੈਂ ਤੁਹਾਡੀ ਖੇਤੀ ਵਿੱਚ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ:\n📍 *ਮੌਸਮ:* ਮੌਸਮ ਜਾਣਨ ਲਈ ਪੁੱਛੋ ਜਾਂ ਲੋਕੇਸ਼ਨ ਪਿੰਨ ਭੇਜੋ।\n📸 *ਫਸਲ ਡਾਕਟਰ:* ਬਿਮਾਰ ਪੌਦੇ ਦੀ ਫੋਟੋ ਭੇਜੋ ਅਤੇ ਤੁਰੰਤ ਇਲਾਜ ਪਾਓ!\n🌱 *ਮੰਡੀ ਭਾਅ:* ਫਸਲਾਂ ਦੇ ਤਾਜ਼ਾ ਰੇਟ ਪੁੱਛੋ।\n🤖 *ਸਲਾਹ:* ਖਾਦ, ਬਿਮਾਰੀਆਂ ਜਾਂ ਪੀਐਮ-ਕਿਸਾਨ ਬਾਰੇ ਪੁੱਛੋ।\n🎙️ *ਆਵਾਜ਼ ਮੋਡ:* ਆਵਾਜ਼ ਵਿੱਚ ਜਵਾਬ ਸੁਣਨ ਲਈ ਵੌਇਸ ਨੋਟ ਭੇਜੋ ਜਾਂ 'voice' ਲਿਖੋ!\n\n*(⚙️ ਸੈਟਿੰਗਜ਼: ਜਗ੍ਹਾ ਬਦਲਣ ਲਈ 'Change location' ਲਿਖੋ ਜਾਂ ਭਾਸ਼ਾ ਬਦਲਣ ਲਈ 1, 2, 3, 4 ਭੇਜੋ)*"
    }
    return manuals.get(lang_code, manuals["1"])

def get_location_prompt(lang_code: str) -> str:
    prompts = {
        "1": "To complete your setup, please reply with your **City or State** name (e.g., Pune, Punjab).",
        "2": "अपना सेटअप पूरा करने के लिए, कृपया अपने **शहर या राज्य** का नाम लिखकर भेजें (उदा. भोपाल, पंजाब)।",
        "3": "तुमची प्रोफाईल पूर्ण करण्यासाठी, कृपया तुमच्या **शहराचे किंवा राज्याचे** नाव लिहून पाठवा (उदा. नाशिक, महाराष्ट्र).",
        "4": "ਆਪਣੀ ਪ੍ਰੋਫਾਈਲ ਪੂਰੀ ਕਰਨ ਲਈ, ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ **ਸ਼ਹਿਰ ਜਾਂ ਰਾਜ** ਦਾ ਨਾਮ ਲਿਖ ਕੇ ਭੇਜੋ (ਉਦਾਹਰਣ: ਲੁਧਿਆਣਾ, ਪੰਜਾਬ)।"
    }
    return prompts.get(lang_code, prompts["1"])

def get_live_weather(lat: float = None, lon: float = None, city_name: str = "New Delhi") -> str:
    try:
        if lat is None or lon is None:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
            geo_res = requests.get(geo_url, timeout=5).json()
            if geo_res.get("results"):
                lat, lon = geo_res["results"][0]["latitude"], geo_res["results"][0]["longitude"]
                city_name = geo_res["results"][0]["name"]
            else:
                lat, lon = 28.6139, 77.2090
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code&forecast_days=1"
        res = requests.get(weather_url, timeout=5).json()
        current = res.get("current", {})
        temp, humidity, precip = current.get("temperature_2m", "N/A"), current.get("relative_humidity_2m", "N/A"), current.get("precipitation", 0)
        rain_status = "Rain expected. Delay chemical spraying." if precip > 0 else "Clear skies, favorable for spraying and field work."
        return f"Weather for {city_name}: Temperature is {temp}°C, Humidity at {humidity}%. {rain_status}"
    except Exception:
        return "Current regional weather is 31°C with clear skies. Suitable for general farming operations."

def query_agricultural_llm(user_prompt: str, user_lang: str, image_base64: str = None, mime_type: str = "image/jpeg") -> str:
    try:
        lang_names = {"1": "English", "2": "Hindi", "3": "Marathi", "4": "Punjabi"}
        target_name = lang_names.get(user_lang, "English")
        
        system_instruction = f"""
You are Krishi-Mitra, an expert AI Agricultural Scientist and Farmer Assistant. Provide clear, practical farming advice.
- Respond directly in {target_name} script (Devanagari for Hindi/Marathi, Gurmukhi for Punjabi).
- Use WhatsApp formatting: wrap key terms or headers in *asterisks* for bold text.
- Use emojis and bullet points to make it highly readable.
- Keep answers actionable and under 3 short paragraphs.
"""
        parts = [{"text": user_prompt}]
        if image_base64:
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_base64}})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"system_instruction": {"parts": [{"text": system_instruction}]}, "contents": [{"role": "user", "parts": parts}]}
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}).json()

        if "error" in res:
            url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-pro:generateContent?key={GEMINI_API_KEY}"
            res = requests.post(url_fallback, json=payload, headers={"Content-Type": "application/json"}).json()

        if "candidates" in res and len(res["candidates"]) > 0:
            return res["candidates"][0]["content"]["parts"][0]["text"].strip()
        return "I couldn't process that due to an API error. Please ask again."
    except Exception as e:
        print(f"Gemini API Exception: {e}")
        return "I am Krishi-Mitra, your farming advisor. Please ask me about crop diseases, fertilizers, weather, or Mandi rates."

# ==================== ASYNCHRONOUS WORKER ====================
def process_query_async(sender_phone: str, query_text: str, media_url: str, media_type: str, lat: str, lon: str, user_lang: str, user_location: str):
    print(f"\n[{sender_phone}] Starting background task (Location: {user_location})...")
    
    stt_langs = {"1": "en-IN", "2": "hi-IN", "3": "mr-IN", "4": "pa-IN"}
    tts_langs = {"1": "en", "2": "hi", "3": "mr", "4": "pa"}
    stt_target, tts_target = stt_langs.get(user_lang, "en-IN"), tts_langs.get(user_lang, "en")
    
    query_text_clean = ""
    session_id = uuid.uuid4().hex[:8] 
    image_base64 = None
    mime_type = "image/jpeg"

    # 1. Process Media (Voice Note OR Image)
    if media_url:
        if media_type.startswith("audio"):
            print(f"[{sender_phone}] Downloading voice note...")
            response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_TOKEN))
            clean_phone = re.sub(r'\D', '', sender_phone)
            in_file = f"static/in_{clean_phone}_{session_id}.ogg"
            wav_file = f"static/in_{clean_phone}_{session_id}.wav"
            
            with open(in_file, "wb") as f: f.write(response.content)

            try:
                audio = AudioSegment.from_file(in_file, format="ogg")
                audio.export(wav_file, format="wav")
                r = sr.Recognizer()
                with sr.AudioFile(wav_file) as source:
                    audio_data = r.record(source)
                    query_text = r.recognize_google(audio_data, language=stt_target)
                print(f"[{sender_phone}] Transcribed Speech: {query_text}")
            except Exception:
                fail_msg = "Sorry, I could not hear that clearly. Please send a text."
                if tts_target != "en": fail_msg = GoogleTranslator(source="en", target=tts_target).translate(fail_msg)
                twilio_client.messages.create(from_=TWILIO_SANDBOX_NUMBER, body=fail_msg, to=sender_phone)
                return
            finally:
                if os.path.exists(in_file): os.remove(in_file)
                if os.path.exists(wav_file): os.remove(wav_file)
        
        elif media_type.startswith("image"):
            print(f"[{sender_phone}] Downloading crop image for AI Diagnosis...")
            response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_TOKEN))
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            mime_type = media_type

    if query_text:
        query_text_clean = query_text.lower().strip()
    
    # 2. Location Pin Processing
    if lat and lon:
        weather_info = get_live_weather(lat=float(lat), lon=float(lon), city_name="Your Location")
        final_text = query_agricultural_llm(f"Farmer shared GPS ({lat}, {lon}). Live weather: '{weather_info}'. Provide concise localized farm advisory.", user_lang)

    # 3. Image/Vision Processing (Crop Doctor)
    elif image_base64:
        print(f"[{sender_phone}] Routing image to Gemini Vision API...")
        loc_context = f" I am farming in {user_location}." if user_location and user_location != 'PENDING' else ""
        vision_prompt = query_text if query_text else f"Please analyze this crop image.{loc_context} Identify the plant and any diseases, pests, or nutrient deficiencies visible. Recommend an actionable treatment plan."
        final_text = query_agricultural_llm(vision_prompt, user_lang, image_base64=image_base64, mime_type=mime_type)

    # 4. Mandi Price Direct Lookup
    elif query_text_clean and any(crop in query_text_clean for crop in MANDI_DATABASE):
        matched_crop = next(crop for crop in MANDI_DATABASE if crop in query_text_clean)
        final_text = query_agricultural_llm(f"Farmer asking for '{matched_crop}'. Benchmark rate: {MANDI_DATABASE[matched_crop]}. Provide friendly market insight.", user_lang)

    # 5. General LLM Farming Conversation & Smart Text Weather
    elif query_text_clean:
        if any(w in query_text_clean for w in ["weather", "mausam", "paus", "rain", "मौसम", "हवामान", "ਮੌਸਮ"]):
            hub = user_location if user_location and user_location != 'PENDING' else "New Delhi"
            weather_info = get_live_weather(city_name=hub)
            final_text = query_agricultural_llm(f"Farmer asked: '{query_text}'. Their set location is {hub}. Live data: '{weather_info}'. Provide a brief localized weather advisory.", user_lang)
        else:
            print(f"[{sender_phone}] Routing text to Gemini Agricultural Brain...")
            loc_context = f"\n(Farmer's Registered Location: {user_location})" if user_location and user_location != 'PENDING' else ""
            final_text = query_agricultural_llm(query_text + loc_context, user_lang)
    else:
        final_text = get_full_manual(user_lang)

    # 6. Check if Voice Delivery is Requested
    wants_voice = False
    if media_url and media_type.startswith("audio"): 
        wants_voice = True
    elif query_text_clean and any(w in query_text_clean for w in ["voice", "audio", "bol", "sunna", "awaz", "speak", "listen", "ਆਵਾਜ਼"]):
        wants_voice = True

    audio_reply_url = None
    if wants_voice:
        print(f"[{sender_phone}] Generating audio file...")
        clean_phone = re.sub(r'\D', '', sender_phone)
        out_file_name = f"out_{clean_phone}_{session_id}.mp3"
        out_file_path = f"static/{out_file_name}"
        try:
            tts = gTTS(text=final_text, lang=tts_target)
            tts.save(out_file_path)
            audio_reply_url = f"{BASE_URL}/static/{out_file_name}"
        except Exception as e:
            print(f"TTS Generation Error: {e}")
    else:
        if query_text_clean not in GREETINGS:  
            footer_tips = {
                "1": "\n\n*(Reply with 'voice' to get an audio note next time)*",
                "2": "\n\n*(बोलकर जवाब सुनने के लिए अगले मैसेज में 'voice' लिखें)*",
                "3": "\n\n*(ऑडिओमध्ये उत्तर ऐकण्यासाठी पुढील मेसेजमध्ये 'voice' लिहा)*",
                "4": "\n\n*(ਆਵਾਜ਼ ਵਿੱਚ ਜਵਾਬ ਸੁਣਨ ਲਈ ਅਗਲੇ ਮੈਸੇਜ ਵਿੱਚ 'voice' ਲਿਖੋ)*"
            }
            final_text += footer_tips.get(user_lang, footer_tips["1"])

    # 7. Deliver WhatsApp Messages Separately
    try:
        twilio_client.messages.create(from_=TWILIO_SANDBOX_NUMBER, body=final_text, to=sender_phone)
        if audio_reply_url:
            twilio_client.messages.create(from_=TWILIO_SANDBOX_NUMBER, media_url=[audio_reply_url], to=sender_phone)
            
        print(f"[{sender_phone}] Successfully delivered response.")

        if query_text:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO logs (phone, query_text) VALUES (%s, %s)", (sender_phone, query_text))
            conn.commit()
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Delivery Error: {e}")

# ==================== FASTAPI WEBHOOK ENDPOINT ====================
@app.post("/whatsapp/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    sender_phone = form.get("From", "")
    incoming_msg = form.get("Body", "").strip()
    media_url = form.get("MediaUrl0")
    media_type = form.get("MediaContentType0", "") 
    lat, lon = form.get("Latitude"), form.get("Longitude")

    resp = MessagingResponse()
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT lang, location FROM users WHERE phone = %s", (sender_phone,))
        user_record = cursor.fetchone()

        # New User Registration Pipeline
        if not user_record:
            if incoming_msg in ["1", "2", "3", "4"]:
                cursor.execute("INSERT INTO users (phone, lang, location) VALUES (%s, %s, %s)", (sender_phone, incoming_msg, 'PENDING'))
                conn.commit()
                # Send the manual and ask for location immediately
                resp.message(get_full_manual(incoming_msg) + "\n\n" + get_location_prompt(incoming_msg))
                return Response(content=str(resp), media_type="application/xml")
            else:
                menu = "Namaste! Welcome to Krishi-Mitra 🌾\n\nPlease select your language / ਭਾਸ਼ਾ ਚੁਣੋ:\n1️⃣ English\n2️⃣ हिन्दी (Hindi)\n3️⃣ मराठी (Marathi)\n4️⃣ ਪੰਜਾਬੀ (Punjabi)\n\nReply with 1, 2, 3, or 4 to start."
                resp.message(menu)
                return Response(content=str(resp), media_type="application/xml")

        user_lang, user_location = user_record[0], user_record[1]

        # 1. Greetings Bypass (Shows Manual)
        if incoming_msg.lower() in GREETINGS and not media_url:
            message_body = get_full_manual(user_lang)
            if user_location == 'PENDING':
                message_body += "\n\n" + get_location_prompt(user_lang)
            resp.message(message_body)
            return Response(content=str(resp), media_type="application/xml")

        # 2. Change Language Trigger
        if incoming_msg in ["1", "2", "3", "4"]:
            cursor.execute("UPDATE users SET lang = %s WHERE phone = %s", (incoming_msg, sender_phone))
            conn.commit()
            confirmations = {"1": "Language updated to English.", "2": "भाषा बदलकर हिन्दी कर दी गई है।", "3": "भाषा मराठीमध्ये बदलली आहे.", "4": "ਭਾਸ਼ਾ ਪੰਜਾਬੀ ਵਿੱਚ ਬਦਲ ਦਿੱਤੀ ਗਈ ਹੈ।"}
            resp.message(f"{confirmations.get(incoming_msg)}\n\n{get_full_manual(incoming_msg)}")
            return Response(content=str(resp), media_type="application/xml")

        # 3. Request Location Change Command
        if incoming_msg and any(kw in incoming_msg.lower() for kw in CHANGE_LOC_KEYWORDS):
            cursor.execute("UPDATE users SET location = 'PENDING' WHERE phone = %s", (sender_phone,))
            conn.commit()
            resp.message(get_location_prompt(user_lang))
            return Response(content=str(resp), media_type="application/xml")

        # 4. Save Pending Location
        if user_location == 'PENDING' and incoming_msg and not media_url and not lat:
            clean_location = incoming_msg.strip()
            cursor.execute("UPDATE users SET location = %s WHERE phone = %s", (clean_location, sender_phone))
            conn.commit()
            
            confirmations = {
                "1": f"📍 Location saved as *{clean_location}*. You are all set! Ask me anything.",
                "2": f"📍 आपकी लोकेशन *{clean_location}* सेव हो गई है। अब आप अपने सवाल पूछ सकते हैं।",
                "3": f"📍 तुमचे ठिकाण *{clean_location}* सेव्ह झाले आहे. आता मला काहीही विचारा.",
                "4": f"📍 ਤੁਹਾਡੀ ਲੋਕੇਸ਼ਨ *{clean_location}* ਸੇਵ ਹੋ ਗਈ ਹੈ। ਹੁਣ ਤੁਸੀਂ ਕੁਝ ਵੀ ਪੁੱਛ ਸਕਦੇ ਹੋ।"
            }
            resp.message(confirmations.get(user_lang, confirmations["1"]))
            return Response(content=str(resp), media_type="application/xml")

        # 5. Delegate all agronomy/weather/image queries to background task
        background_tasks.add_task(process_query_async, sender_phone, incoming_msg, media_url, media_type, lat, lon, user_lang, user_location)
        return Response(content="<Response></Response>", media_type="application/xml")

    except Exception as e:
        print(f"Webhook Error: {e}")
        return Response(content="<Response></Response>", media_type="application/xml")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)