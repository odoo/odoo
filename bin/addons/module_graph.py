#!/usr/bin/python
# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be)
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contact a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################


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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

