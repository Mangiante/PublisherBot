import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RestartHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = subprocess.Popen(self.command, shell=True)

    def on_any_event(self, event):
        if event.src_path.endswith(".py"):
            print(f"Modification détectée dans : {event.src_path}. Redémarrage du bot...")
            self.process.terminate()
            self.process = subprocess.Popen(self.command, shell=True)


if __name__ == "__main__":
    path = "."  # Répertoire à surveiller (racine du projet)
    command = "python3 PublisherBot.py"  # Commande pour exécuter votre bot

    event_handler = RestartHandler(command)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    print("Surveillance des fichiers .py activée. Modifiez un fichier pour redémarrer le bot.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
