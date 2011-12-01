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

"""
Some functions related to the os and os.path module
"""

import os
from os.path import join as opj

def listdir(dir, recursive=False):
	"""Allow to recursively get the file listing"""
	dir = os.path.normpath(dir)
	if not recursive:
		return os.listdir(dir)

	res = []
	for root, dirs, files in walksymlinks(dir):
		root = root[len(dir)+1:]
		res.extend([opj(root, f) for f in files])
	return res

def walksymlinks(top, topdown=True, onerror=None):
    """
    same as os.walk but follow symlinks
    attention: all symlinks are walked before all normals directories
    """
    for dirpath, dirnames, filenames in os.walk(top, topdown, onerror):
        if topdown:
            yield dirpath, dirnames, filenames

        symlinks = filter(lambda dirname: os.path.islink(os.path.join(dirpath, dirname)), dirnames)
        for s in symlinks:
            for x in walksymlinks(os.path.join(dirpath, s), topdown, onerror):
                yield x

        if not topdown:
            yield dirpath, dirnames, filenames



if __name__ == '__main__':
	from pprint import pprint as pp
	pp(listdir('../report', True))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
