"""
Helper class for using logging as trace file object
"""

import logging

class logging_file_class:

    def __init__(self, logging_level):
        self._logging_level = logging_level

    def write(self, msg):
        logging.log(self._logging_level, msg[:-1])

    def flush(self):
        return

logging_file_obj = logging_file_class(logging.DEBUG)
