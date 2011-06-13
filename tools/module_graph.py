#!/usr/bin/env python
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
import optparse
import sys
import glob

# TODO use the same function provided in openerp.modules
def load_information_from_description_file(module):
    """
    :param module: The name of the module (sale, purchase, ...)
    """
    for filename in ['__openerp__.py', '__terp__.py']:
        description_file = os.path.join(module, filename)
        if os.path.isfile(description_file):
            return eval(file(description_file).read())

    return {}

def get_valid_path(paths, module):
    for path in paths:
        full = os.path.join(path, module)
        if os.path.exists(full):
            return full
    return None

parser = optparse.OptionParser(usage="%prog [options] [module1 [module2 ...]]")
parser.add_option("-p", "--addons-path", dest="path", help="addons directory", action="append")
(opt, args) = parser.parse_args()

modules = []
if not opt.path:
    opt.path = ["."]

if not args:
    for path in opt.path:
        modules += map(os.path.dirname, glob.glob(os.path.join(path, '*', '__openerp__.py')))
        modules += map(os.path.dirname, glob.glob(os.path.join(path, '*', '__terp__.py')))
else:
    for module in args:
        valid_path = get_valid_path(opt.path, module)
        if valid_path:
            modules.append(valid_path)

all_modules = set(map(os.path.basename, modules))
print 'digraph G {'
while len(modules):
    f = modules.pop(0)
    module_name = os.path.basename(f)
    all_modules.add(module_name)
    info = load_information_from_description_file(f)
    if info.get('installable', True):
        for name in info.get('depends',[]):
            valid_path = get_valid_path(opt.path, name)
            if name not in all_modules:
                if valid_path:
                    modules.append(valid_path)
                else:
                    all_modules.add(name)
                    print '\t%s [color=red]' % (name,)
            print '\t%s -> %s;' % (module_name, name)
print '}'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

