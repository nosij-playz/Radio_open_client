import io
import subprocess
from flask import Response, send_file
from gtts import gTTS
import yt_dlp
from flask import Flask, render_template, jsonify, request
from db import get_db_connection


import os
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

import threading
import time

# Global alert state
alert_data = {"type": None, "message": None}

def monitor_alerts():
    while True:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Check ai_alert
        cursor.execute("SELECT * FROM ai_alert WHERE id=1")
        ai = cursor.fetchone()
        # Check user_alert
        cursor.execute("SELECT * FROM user_alert WHERE id=1")
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if ai and ai.get('message'):
            alert_data["type"] = "ai"
            alert_data["message"] = ai["message"]
        elif user and user.get('message'):
            alert_data["type"] = "user"
            alert_data["message"] = user["message"]
        else:
            alert_data["type"] = None
            alert_data["message"] = None
        time.sleep(2)

# Start monitor thread
threading.Thread(target=monitor_alerts, daemon=True).start()

# Helper to get status_server row
# Helper to get status_server row
def get_status():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM status_server WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

# Main page
# Main page
@app.route("/")
def index():
    return render_template("index.html")

# Get music link for id=1
# Get music link for id=1
def get_music():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM music WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

# Stream YouTube audio as live
@app.route("/stream")
def stream():
    status_row = get_status()
    if status_row and status_row['status'] in ('freq', 'stop'):
        print(f"[MUSIC] Blocked: status is {status_row['status']}, not streaming audio.")
        return "", 204
    music = get_music()
    if not music or not music['link']:
        print("No music link found in DB.")
        return "No music link found", 404
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'extract_flat': False,
        'outtmpl': '-',
    }
    url = music['link']
    print(f"[STREAM] /stream called. Current music link: {url}")
    def generate():
        print(f"[MUSIC] Streaming music from: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
        # Use ffmpeg to stream audio
        ffmpeg_cmd = [
            'ffmpeg', '-i', audio_url, '-f', 'mp3', '-vn', '-'
        ]
        p = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                data = p.stdout.read(4096)
                if not data:
                    break
                yield data
        finally:
            p.kill()
        print("[MUSIC] Music streaming ended.")
    return Response(generate(), mimetype='audio/mpeg')

# TTS for alert
@app.route("/tts_alert")
def tts_alert():
    status_row = get_status()
    if status_row and status_row['status'] in ('freq', 'stop'):
        print(f"[ALERT] Blocked: status is {status_row['status']}, not playing alert audio.")
        return "", 204
    if not alert_data["message"]:
        print("[ALERT] No alert message to play.")
        return "", 204
    print(f"[ALERT] Playing TTS alert: {alert_data['message']}")
    msg = alert_data["message"]
    # Detect Malayalam (simple unicode range check)
    def is_malayalam(text):
        for c in text:
            if '\u0D00' <= c <= '\u0D7F':
                return True
        return False
    if is_malayalam(msg):
        try:
            tts = gTTS(text=msg, lang='ml', slow=True)
        except Exception as e:
            print(f"[ALERT] Malayalam TTS failed, falling back to English: {e}")
            tts = gTTS(text=msg, lang='en')
    else:
        tts = gTTS(text=msg, lang='en')
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return send_file(buf, mimetype='audio/mpeg')

# Start music (play)
# Start music (play)
@app.route("/start")
def start():
    status_row = get_status()
    if status_row and status_row['status'] in ('freq', 'stop'):
        print("[START] Blocked: status is FREQ or STOP.")
        return jsonify({"play": False, "reason": "System is in FREQ or STOP mode."})
    if status_row and status_row['status'] in ('net', 'both'):
        music = get_music()
        if music and music['link']:
            print(f"[START] /start called. Returning music link: {music['link']}")
            return jsonify({"play": True, "link": music['link']})
    print("[START] /start called but no music available.")
    return jsonify({"play": False})

# Endpoint to get alert state
@app.route("/alert")
def alert():
    return jsonify(alert_data)

# Stop music (pause)
@app.route("/stop")
def stop():
    return jsonify({"play": False})

@app.route("/status")
def status():
    status_row = get_status()
    # Add current music link for debugging
    music = get_music()
    if music and music.get('link'):
        status_row['link'] = music['link']
    return jsonify(status_row)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)