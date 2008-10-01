import threading
import ftpserver
import authorizer
import abstracted_fs

PORT = 8021
HOST = ''

class ftp_server(threading.Thread):
	def run(self):
		autho = authorizer.authorizer()
		ftpserver.FTPHandler.authorizer = autho
		ftpserver.max_cons = 300
		ftpserver.max_cons_per_ip = 50
		ftpserver.FTPHandler.abstracted_fs = abstracted_fs.abstracted_fs
		address = (HOST, PORT)
		ftpd = ftpserver.FTPServer(address, ftpserver.FTPHandler)
		ftpd.serve_forever()

ds = ftp_server()
ds.start()

