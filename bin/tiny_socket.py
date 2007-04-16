import socket
import cPickle
import marshal

class Myexception(Exception):
	def __init__(self, faultCode, faultString):
		self.faultCode = faultCode
		self.faultString = faultString

class mysocket:
	def __init__(self, sock=None):
		if sock is None:
			self.sock = socket.socket(
			socket.AF_INET, socket.SOCK_STREAM)
		else:
			self.sock = sock
		self.sock.settimeout(60)
	def connect(self, host, port=False):
		if not port:
			protocol, buf = host.split('//')
			host, port = buf.split(':')
		self.sock.connect((host, int(port)))
	def disconnect(self):
		self.sock.shutdown(socket.SHUT_RDWR)
		self.sock.close()
	def mysend(self, msg, exception=False, traceback=None):
		msg = cPickle.dumps([msg,traceback])
		size = len(msg)
		self.sock.send('%8d' % size)
		self.sock.send(exception and "1" or "0")
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
		buf = self.sock.recv(1)
		if buf != "0":
			exception = buf
		else:
			exception = False
		msg = ''
		while len(msg) < size:
			chunk = self.sock.recv(size-len(msg))
			if chunk == '':
				raise RuntimeError, "socket connection broken"
			msg = msg + chunk
		res = cPickle.loads(msg)
		if isinstance(res[0],Exception):
			if exception:
				raise Myexception(exception, str(res[0]), str(res[1]))
			raise res[0]
		else:
			return res[0]

