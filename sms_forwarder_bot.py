import os
import json
import requests
import datetime

CONFIG_FILE = "sms_forwarder_config.txt"
LAST_TIME_FILE = "last_forward_time.txt"

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

def main():
    if not os.path.exists(CONFIG_FILE):
        filters, token, users = setup_config()
    else:
        filters, token, users = load_config()

    last_forward_time = load_last_forward_time()
    sms_data = os.popen("termux-sms-list -l 50").read()

    try:
        sms_list = json.loads(sms_data)
    except Exception as e:
        print(f"❌ Failed to parse SMS JSON: {e}")
        return

    new_last_time = last_forward_time

    for sms in sorted(sms_list, key=lambda x: x['received']):  # sort by received time ascending
        try:
            received_time = datetime.datetime.fromisoformat(sms['received'])
        except:
            continue

        if last_forward_time and received_time <= last_forward_time:
            continue  # skip already processed SMS

        body = sms.get("body", "").lower()
        sender = sms.get("from", "Unknown")
        matched = any(f in body for f in filters)

        if matched:
            msg = f"📩 *SMS Matched Filter*\n\nFrom: {sender}\nTime: {sms['received']}\n\n{sms.get('body', '')}"
            for chat_id in users:
                send_telegram_message(token, chat_id, msg)
            print(f"Forwarded SMS received at {sms['received']}")

            # Update new_last_time to latest SMS forwarded
            if (not new_last_time) or (received_time > new_last_time):
                new_last_time = received_time

    # Save the last forwarded SMS time to file
    if new_last_time:
        save_last_forward_time(new_last_time)
    else:
        print("No new SMS matched filters since last run.")

if __name__ == "__main__":
    main()
