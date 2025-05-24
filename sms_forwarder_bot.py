import os
import json
import requests
import datetime
import time
import sys

CONFIG_FILE = "sms_forwarder_config.txt"
LAST_TIME_FILE = "last_forward_time.txt"

def setup_config():
    print("🔧 Initial Setup: Configuration File Not Found.")
    filters = input("Enter keyword filter(s), comma-separated (e.g., otp,bank,payment): ").lower().split(",")
    token = input("Enter your Telegram Bot Token (from @BotFather): ").strip()
    users = input("Enter recipient Telegram Chat IDs (comma-separated from @userinfobot): ").split(",")
    interval = input("Enter check interval in seconds (default 15): ").strip()
    interval = int(interval) if interval.isdigit() else 15

    with open(CONFIG_FILE, "w") as f:
        f.write(','.join(filters) + "\n")
        f.write(token + "\n")
        f.write(','.join(users) + "\n")
        f.write(str(interval) + "\n")

    return filters, token, users, interval

def load_config():
    with open(CONFIG_FILE, "r") as f:
        lines = f.read().splitlines()
    filters = lines[0].split(",")
    token = lines[1].strip()
    users = [u.strip() for u in lines[2].split(",")]
    interval = int(lines[3]) if len(lines) >= 4 and lines[3].isdigit() else 15
    return filters, token, users, interval

def load_last_forward_time():
    if not os.path.exists(LAST_TIME_FILE):
        return None
    with open(LAST_TIME_FILE, "r") as f:
        time_str = f.read().strip()
    try:
        return datetime.datetime.fromisoformat(time_str)
    except:
        return None

def save_last_forward_time(dt):
    with open(LAST_TIME_FILE, "w") as f:
        f.write(dt.isoformat())

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload)
        if r.status_code == 200:
            print(f"✅ Message sent to {chat_id}")
        else:
            print(f"❌ Failed to send message to {chat_id} | Status code: {r.status_code}")
    except Exception as e:
        print(f"❌ Failed to send message to {chat_id}: {e}")

def check_new_sms(filters, token, users, last_forward_time):
    sms_data = os.popen("termux-sms-list -l 50").read()
    try:
        sms_list = json.loads(sms_data)
    except Exception as e:
        print(f"❌ Failed to parse SMS JSON: {e}")
        return last_forward_time

    new_last_time = last_forward_time

    for sms in sorted(sms_list, key=lambda x: x['received']):  # sort by time ascending
        try:
            received_time = datetime.datetime.fromisoformat(sms['received'])
        except:
            continue

        if last_forward_time and received_time <= last_forward_time:
            continue

        body = sms.get("body", "").lower()
        sender = sms.get("from") or sms.get("address") or sms.get("number") or "Unknown"
        matched = any(f in body for f in filters)

        if matched:
            device_name = get_device_name()
            msg = (
                f"📩 *SMS Received from {device_name}* 📩\n"
                "------------------------------------------\n"
                f"*From:* {sender}\n"
                f"*Time:* {sms['received']}\n"
                "------------------------------------------\n"
                f"{sms.get('body', '')}\n"
                "------------------------------------------"
            )
            for chat_id in users:
                send_telegram_message(token, chat_id, msg)
            print(f"Forwarded SMS received at {sms['received']}")

            if not new_last_time or received_time > new_last_time:
                new_last_time = received_time

    if new_last_time:
        save_last_forward_time(new_last_time)
    else:
        print("No new SMS matched filters since last check.")

    return new_last_time

def get_device_name():
    try:
        return os.popen("getprop net.hostname").read().strip()
    except:
        return "Unknown Device"

def main():
    reset = "--reset" in sys.argv

    if reset or not os.path.exists(CONFIG_FILE):
        filters, token, users, interval = setup_config()
    else:
        filters, token, users, interval = load_config()

    last_forward_time = load_last_forward_time()
    print(f"📡 Starting SMS forwarder... Checking every {interval} seconds.\n")

    while True:
        last_forward_time = check_new_sms(filters, token, users, last_forward_time)
        time.sleep(interval)

    last_forward_time = load_last_forward_time()

    print(f"📡 Starting SMS forwarder... Checking every {interval} seconds.\n")

    while True:
        last_forward_time = check_new_sms(filters, token, users, last_forward_time)
        time.sleep(interval)

if __name__ == "__main__":
    main()
