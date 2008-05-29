#!/usr/bin/python

import os
import sys
import glob

if len(sys.argv) == 2 and (sys.argv[1] in ['-h', '--help']):
    print >>sys.stderr, 'Usage: module_graph.py [module1 module2 module3]\n\tWhen no module is specified, all modules in current directory are used'
    sys.exit(1)

modules = sys.argv[1:]
if not len(modules):
    modules = map(os.path.dirname, glob.glob(os.path.join('*', '__terp__.py')))

done = []

print 'digraph G {'
while len(modules):
	f = modules.pop(0)
	done.append(f)
	if os.path.isfile(os.path.join(f,"__terp__.py")):
		info=eval(file(os.path.join(f,"__terp__.py")).read())
		if info.get('installable', True):
			for name in info['depends']:
				if name not in done+modules:
					modules.append(name)
				print '\t%s -> %s;' % (f, name)
print '}'
