import logging.handlers

RUNBOT = 25


class WatchedFileHandler(logging.handlers.WatchedFileHandler):
    def __init__(self, filename):
        self.errors = None  # py38
        super().__init__(filename)
        # Unfix bpo-26789, in case the fix is present
        self._builtin_open = None

    def _open(self):
        return open(self.baseFilename, self.mode, encoding=self.encoding, errors=self.errors)


def patch_module():
    logging.RUNBOT = RUNBOT
    logging.addLevelName(RUNBOT, "RUNBOT")
    logging._levelToName[RUNBOT] = "INFO"  # displayed as info in log
    logging.Logger.runbot = \
        lambda self, msg, *args, **kwargs: self.log(RUNBOT, msg, *args, **kwargs)
    logging.handlers.WatchedFileHandler = WatchedFileHandler
