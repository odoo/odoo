from . import controllers, models, wizard
from .hooks import post_init_hook
from .models import queue_consumer


def post_load():
    """Start the invoice.result consumer thread after the registry loads.

    One daemon thread per Odoo process reads ``invoice.result`` and applies
    JWT-signed worker results / lifecycle signals (see
    ``models/queue_consumer.py``).
    """
    queue_consumer.start_result_consumer()
