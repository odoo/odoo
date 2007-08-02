#!/usr/bin/python

import os
import sys

if not len(sys.argv)>1:
	raise 'Usage: gen_graph.sh module1 module2 module3'

modules = sys.argv[1:]
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
