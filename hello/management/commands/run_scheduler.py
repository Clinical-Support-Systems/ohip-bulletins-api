from django.core.management.base import BaseCommand
from hello.scheduler import start_scheduler

class Command(BaseCommand):
    help = 'Starts the scheduler for the Django app.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting scheduler...')
        start_scheduler()