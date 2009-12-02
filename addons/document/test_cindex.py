#!/usr/bin/python

import sys
import os
import glob

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")

parser.add_option("-C", "--content",
                  action="store_true", dest="docontent", default=False,
                  help="Disect content, rather than the file.")

(options, args) = parser.parse_args()

import content_index, std_index

from content_index import cntIndex

for fname in args:
	try:
		if options.docontent:
			fp = open(fname,'rb')
			content = fp.read()
			fp.close()
			res = cntIndex.doIndex(content,fname,None,None,True)
		else:
			res = cntIndex.doIndex(None, fname, None, fname,True)

		if res:
			print "Result: ", res[0]
			print res[1]
		else:
			print "No result"
	except Exception,e:
		import traceback,sys
		tb_s = reduce(lambda x, y: x+y, traceback.format_exception( sys.exc_type, sys.exc_value, sys.exc_traceback))
		print "Traceback:",tb_s
		print "Exception: ",e
		

#eof
