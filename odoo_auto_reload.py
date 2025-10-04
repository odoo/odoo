import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import subprocess

class ReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py') or event.src_path.endswith('.xml'):
            print(f"File changed: {event.src_path}, restarting Odoo...")
            subprocess.call(["./odoo-bin", "--config=odoo.conf", "--dev=all", "-u", "estate"])

if __name__ == "__main__":
    event_handler = ReloadHandler()
    observer = Observer()
    observer.schedule(event_handler, path='./', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
