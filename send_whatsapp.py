import time
import json
import pywhatkit
import os

json_path = "C:/odoo/send_queue.json"

while True:
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            phone = data['phone']
            msg = data['message']
            print(f"Sending WhatsApp to {phone}: {msg}")

            pywhatkit.sendwhatmsg_instantly(phone, msg, wait_time=10, tab_close=False)

            os.remove(json_path)  # Delete file after sending

        except Exception as e:
            print("Error:", e)

    time.sleep(5)  # Wait 5 seconds before checking again