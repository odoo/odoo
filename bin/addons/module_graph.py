# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

# TODO handle the case of zip modules

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
                if not os.path.exists(name):
                    print '\t%s [color=red]' % (name,)
                print '\t%s -> %s;' % (f, name)
print '}'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

