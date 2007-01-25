#!/usr/bin/python

import time
import threading

import SimpleXMLRPCServer,signal,sys,xmlrpclib
import SocketServer
import socket
import logging
import os

try:
	from ssl import *
	HAS_SSL = True
except ImportError:
	HAS_SSL = False

_service={}
_group={}
_res_id=1
_res={}

class ServiceEndPointCall(object):
	def __init__(self,id,method):
		self._id=id
		self._meth=method
	def __call__(self,*args):
		_res[self._id]=self._meth(*args)
		return self._id

class ServiceEndPoint(object):
	def __init__(self, name, id):
		self._id = id
		self._meth={}
		s=_service[name]
		for m in s._method:
			self._meth[m]=s._method[m]
	def __getattr__(self, name):
		return ServiceEndPointCall(self._id, self._meth[name])

class Service(object):
	_serviceEndPointID = 0
	def __init__(self, name, audience=''):
		_service[name]=self
		self.__name=name
		self._method={}
		self.exportedMethods=None
		self._response_process=None
		self._response_process_id=None
		self._response=None
		
	def joinGroup(self,name):
		if not name in _group:
			_group[name]={}
		_group[name][self.__name]=self
		
	def exportMethod(self, m):
		if callable(m):
			self._method[m.__name__]=m

	def serviceEndPoint(self,s):
		if Service._serviceEndPointID >= 2**16:
			Service._serviceEndPointID = 0
		Service._serviceEndPointID += 1
		return ServiceEndPoint(s, self._serviceEndPointID)

	def conversationId(self):
		return 1

	def processResponse(self,s,id):
		self._response_process, self._response_process_id = s, id

	def processFailure(self,s,id):
		pass

	def resumeResponse(self,s):
		pass

	def cancelResponse(self,s):
		pass

	def suspendResponse(self,s):
		if self._response_process:
			self._response_process(self._response_process_id,
								   _res[self._response_process_id])
		self._response_process=None
		self._response=s(self._response_process_id)

	def abortResponse(self,error, description, origin, details):
		import tools
		if not tools.config['debug_mode']:
			raise Exception("%s -- %s\n\n%s"%(origin,description,details))
		else:
			raise

	def currentFailure(self,s):
		pass

class LocalService(Service):
	def __init__(self, name):
		self.__name=name
		s=_service[name]
		self._service=s
		for m in s._method:
			setattr(self,m,s._method[m])

class ServiceUnavailable(Exception):
	pass

LOG_DEBUG='debug'
LOG_INFO='info'
LOG_WARNING='warn'
LOG_ERROR='error'
LOG_CRITICAL='critical'

def init_logger():
	from tools import config
	import os

	if config['logfile']:
		logf = config['logfile']
		# test if the directories exist, else create them
		try:
			if not os.path.exists(os.path.dirname(logf)):
				os.makedirs(os.path.dirname(logf))
			try:
				fd = open(logf, 'a')
				handler = logging.StreamHandler(fd)
			except IOError:
				sys.stderr.write("ERROR: couldn't open the logfile\n")
				handler = logging.StreamHandler(sys.stdout)
		except OSError:
			sys.stderr.write("ERROR: couldn't create the logfile directory\n")
			handler = logging.StreamHandler(sys.stdout)
	else:
		handler = logging.StreamHandler(sys.stdout)

	# create a format for log messages and dates
	formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s', '%a, %d %b %Y %H:%M:%S')

	# tell the handler to use this format
	handler.setFormatter(formatter)

	# add the handler to the root logger
	logging.getLogger().addHandler(handler)
	logging.getLogger().setLevel(logging.INFO)


class Logger(object):
	def notifyChannel(self,name,level,msg):
		log = logging.getLogger(name)
		getattr(log,level)(msg)

class Agent(object):
	_timers = []
	_logger = Logger()

	def setAlarm(self, fn, dt, args=[], kwargs={}):
		wait = dt - time.time()
		if wait > 0:
			self._logger.notifyChannel(
					'timers', LOG_DEBUG,
					"Job scheduled in %s seconds for %s.%s" % (wait,
															   fn.im_class.__name__,
												fn.func_name))
			timer = threading.Timer(wait, fn, args, kwargs)
			timer.start()
			self._timers.append(timer)
		for timer in self._timers[:]:
			if not timer.isAlive():
				self._timers.remove(timer)

	def quit(cls):
		for timer in cls._timers:
			timer.cancel()
	quit=classmethod(quit)

class RpcGateway(object):
	def __init__(self, name):
		self.name=name

class Dispatcher(object):
	def __init__(self):
		pass
	def monitor(self,signal):
		pass
	def run(self):
		pass

class xmlrpc(object):
	class RpcGateway(object):
		def __init__(self, name):
			self.name=name

class GenericXMLRPCRequestHandler:
	def _dispatch(self, method, params):
		import traceback
		try:
			n=self.path.split("/")[-1]
#			print "TERP-CALLING:",n,method,params
			s=LocalService(n)
			m=getattr(s,method)
			s._service._response=None
			r=m(*params)
			res=s._service._response
			if res!=None:
#				print "RESPONSE FOUND"
				r=res
#			print "TERP-RETURN :",r
			return r
		except Exception,e:
			print "Exception in call:"
			print '-'*60
			traceback.print_exc(file=sys.stdout)
			print '-'*60
			s=str(e)
			import tools
			if tools.config['debug_mode']:
				import pdb
				tb = sys.exc_info()[2]
				pdb.post_mortem(tb)
			raise xmlrpclib.Fault(1,s)

import tiny_socket

class HttpDaemon(object):
	def __init__(self, interface,port, secure=False):
		self.__port=port
		self.__interface=interface
		self.server = socket.socket( socket.AF_INET, socket.SOCK_STREAM)
		self.server.bind((socket.gethostname(), 8085))
		self.server.listen(5)

	def attach(self,path,gw):
		pass

	def handler(self,signum, frame):
		from tools import config
		self.server.close()
		self.server.close()
		Agent.quit()
		if config['pidfile']:
			os.unlink(config['pidfile'])
		del self.server
		sys.exit(0)

	def start(self):
		signal.signal(signal.SIGINT, self.handler)
		signal.signal(signal.SIGTERM, self.handler)
		class client_thread(threading.Thread):
			def run(self, sock):
				ts = tiny_socket.mysocket(sock)
				msg = ts.myreceive()

				s=LocalService(msg[0])
				m=getattr(s,msg[1])
				s._service._response=None
				r=m(*msg[2:])
				res=s._service._response
				if res!=None:
					r=res
				result = r

				ts.mysend(result)

				return msg

		while 1:
			#accept connections from outside
			(clientsocket, address) = self.server.accept()
			#now do something with the clientsocket
			#in this case, we'll pretend this is a threaded server
			ct = client_thread()
			ct.run(clientsocket)

