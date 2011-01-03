#!/usr/bin/python

import sys
import os
import glob
import time
import logging

from optparse import OptionParser

logging.basicConfig(level=logging.DEBUG)

parser = OptionParser()
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")

parser.add_option("-C", "--content",
                  action="store_true", dest="docontent", default=False,
                  help="Disect content, rather than the file.")

parser.add_option("--delay",
                  action="store_true", dest="delay", default=False,
                  help="delay after the operation, to inspect child processes")

(options, args) = parser.parse_args()

import content_index, std_index

from content_index import cntIndex

for fname in args:
    try:
        if options.docontent:
            fp = open(fname,'rb')
            content = fp.read()
            fp.close()
            res = cntIndex.doIndex(content, fname, None, None, True)
        else:
            res = cntIndex.doIndex(None, fname, None, fname,True)

        if options.verbose:
            for line in res[:5]:
                print line
        if options.delay:
            time.sleep(30)
    except Exception,e:
        import traceback
        tb_s = reduce(lambda x, y: x+y, traceback.format_exception( sys.exc_type, sys.exc_value, sys.exc_traceback))
    except KeyboardInterrupt:
        print "Keyboard interrupt"

#eof
