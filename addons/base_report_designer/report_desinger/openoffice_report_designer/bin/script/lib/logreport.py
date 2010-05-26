import logging
import tempfile
LOG_DEBUG='debug'
LOG_INFO='info'
LOG_WARNING='warn'
LOG_ERROR='error'
LOG_CRITICAL='critical'

def log_detail(self):
    import os
    logger = logging.getLogger()
    logfile_name = os.path.join(tempfile.gettempdir(), "report_designer.log")
    hdlr = logging.FileHandler(logfile_name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

class Logger(object):
    def log_write(self,name,level,msg):
        log = logging.getLogger(name)
        getattr(log,level)(msg)

    def shutdown(self):
        logging.shutdown()

