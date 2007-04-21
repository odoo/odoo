#!/usr/bin/python

import os

print 'digraph G {'
for f in os.listdir('.'):
	if os.path.isfile(os.path.join(f,"__terp__.py")):
		info=eval(file(os.path.join(f,"__terp__.py")).read())
		if info.get('installable', True):
			for name in info['depends']:
				print '\t%s -> %s;' % (f, name)
print '}'
