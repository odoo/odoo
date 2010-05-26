#
# Use this module to retrive the fields you need according to the type
# of the OpenOffice operation:
#  * Insert a Field
#  * Insert a RepeatIn
#

import xmlrpclib
import time

sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/object')

def get(object, level=3, ending=[], ending_excl=[], recur=[], root=''):
	res = sock.execute('terp', 3, 'admin', 'account.invoice', 'fields_get')
	key = res.keys()
	key.sort()
	for k in key:
		if (not ending or res[k]['type'] in ending) and ((not ending_excl) or not (res[k]['type'] in ending_excl)):
			print root+'/'+k

		if res[k]['type'] in recur:
			print root+'/'+k
		if (res[k]['type'] in recur) and (level>0):
			get(res[k]['relation'], level-1, ending, ending_excl, recur, root+'/'+k)

print 'Field selection for a rields', '='*40
get('account.invoice', level=0, ending_excl=['one2many','many2one','many2many','reference'], recur=['many2one'])

print
print 'Field selection for a repeatIn', '='*40
get('account.invoice', level=0, ending=['one2many','many2many'], recur=['many2one'])

