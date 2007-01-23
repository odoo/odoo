import socket
import cPickle
import marshal

class mysocket:
	def __init__(self, sock=None):
		if sock is None:
			self.sock = socket.socket(
			socket.AF_INET, socket.SOCK_STREAM)
		else:
			self.sock = sock
	def connect(self, host, port):
		self.sock.connect((host, port))
	def mysend(self, msg):
		msg = cPickle.dumps(msg)
		size = len(msg)
		self.sock.send('%8d' % size)
		totalsent = 0
		while totalsent < size:
			sent = self.sock.send(msg[totalsent:])
			if sent == 0:
				raise RuntimeError, "socket connection broken"
			totalsent = totalsent + sent
	def myreceive(self):
		size = int(self.sock.recv(8))
		msg = ''
		while len(msg) < size:
			chunk = self.sock.recv(size-len(msg))
			if chunk == '':
				raise RuntimeError, "socket connection broken"
			msg = msg + chunk
		return cPickle.loads(msg)
