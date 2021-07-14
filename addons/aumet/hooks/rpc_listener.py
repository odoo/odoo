import logging
import time


_logger = logging.getLogger(__name__)

def listener(cr, registry):
    while(True):
        _logger.info("this is a stupid listener")
        time.sleep(10)