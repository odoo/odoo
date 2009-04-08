import threading
import ftpserver
import authorizer
import abstracted_fs
import netsvc

from tools import config
PORT = config.get('ftp_server_port', 8021)
HOST = ''

class ftp_server(threading.Thread):
    def log(self, level, message):        
        logger = netsvc.Logger()
        logger.notifyChannel('FTP', level, message)

    def run(self):
        autho = authorizer.authorizer()        
        ftpserver.FTPHandler.authorizer = autho
        ftpserver.max_cons = 300
        ftpserver.max_cons_per_ip = 50
        ftpserver.FTPHandler.abstracted_fs = abstracted_fs.abstracted_fs
        
        ftpserver.log = lambda msg: self.log(netsvc.LOG_INFO, msg)
        ftpserver.logline = lambda msg: None
        ftpserver.logerror = lambda msg: self.log(netsvc.LOG_ERROR, msg)

        address = (HOST, PORT)
        ftpd = ftpserver.FTPServer(address, ftpserver.FTPHandler)
        ftpd.serve_forever()
ds = ftp_server()
ds.start()

