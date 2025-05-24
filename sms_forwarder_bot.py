import os
import json
import requests
import datetime

CONFIG_FILE = "sms_forwarder_config.txt"

def setup_config():
    print("🔧 Initial Setup: Configuration File Not Found.")
    filters = input("Enter keyword filter(s), comma-separated (e.g., otp,bank,payment): ").lower().split(",")
    token = input("Enter your Telegram Bot Token (from @BotFather): ").strip()
    users = input("Enter recipient Telegram Chat IDs (comma-separated): ").split(",")

    with open(CONFIG_FILE, "w") as f:
        f.write(','.join(filters) + "\n")
        f.write(token + "\n")
        f.write(','.join(users) + "\n")

    return filters, token, users

def load_config():
    with open(CONFIG_FILE, "r") as f:
        lines = f.read().splitlines()
    filters = lines[0].split(",")
    token = lines[1].strip()
    users = [u.strip() for u in lines[2].split(",")]
    return filters, token, users

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        r = requests.post(url, data=payload)
        print(f"✅ Message sent to {chat_id} | Status: {r.status_code}")
    except Exception as e:
        print(f"❌ Failed to send message to {chat_id}: {e}")

def main():
    if not os.path.exists(CONFIG_FILE):
        filters, token, users = setup_config()
    else:
        filters, token, users = load_config()

    sms_data = os.popen("termux-sms-list -l 1").read()
    try:
        last_sms = json.loads(sms_data)[0]
        body = last_sms["body"].lower()
        sender = last_sms.get("from", "Unknown")
        received = last_sms["received"]
        matched = any(f in body for f in filters)

        if matched:
            msg = f"📩 *SMS Matched Filter*\n\nFrom: {sender}\nTime: {received}\n\n{last_sms['body']}"
            for chat_id in users:
                send_telegram_message(token, chat_id, msg)
        else:
            print("ℹ️ SMS did not match any filter. Skipping.")

    except Exception as e:
        print(f"❌ Failed to process SMS: {e}")

if __name__ == "__main__":
    main()
