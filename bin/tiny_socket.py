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
		self.sock.settimeout(60)
	def connect(self, host, port):
		self.sock.connect((host, port))
	def disconnect(self):
		self.sock.shutdown(socket.SHUT_RDWR)
		self.sock.close()
	def mysend(self, msg, exception=False):
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
		buf=''
		while len(buf) < 8:
			chunk = self.sock.recv(8 - len(buf))
			if chunk == '':
				raise RuntimeError, "socket connection broken"
			buf += chunk
		size = int(buf)
		msg = ''
		while len(msg) < size:
			chunk = self.sock.recv(size-len(msg))
			if chunk == '':
				raise RuntimeError, "socket connection broken"
			msg = msg + chunk
		res = cPickle.loads(msg)
		if isinstance(res,Exception):
			raise res
		else:
			return res
