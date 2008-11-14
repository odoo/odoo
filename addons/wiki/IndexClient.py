#!/usr/bin/python

import xmlrpclib

tiny_host = 'localhost'
tiny_port = 8000

url = 'http://%s:%s' % (tiny_host, tiny_port)
proxy = xmlrpclib.ServerProxy(url);

proxy.init('terp', 3, 'admin')
print proxy.search('china')