import socket
import gevent.socket as gevent_socket

gevent_socket.getaddrinfo(u'gevent.org', None, socket.AF_INET)
