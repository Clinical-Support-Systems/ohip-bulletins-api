from django.apps import AppConfig
from threading import Thread
from .tasks import update_cache

class HelloConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hello"
    def ready(self):
        thread = Thread(target=update_cache)
        thread.daemon = True  # Daemonize the thread to exit with the main proces
        thread.start()