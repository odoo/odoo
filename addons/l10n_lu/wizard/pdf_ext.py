# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

""" Copyright (c) 2003-2007 LOGILAB S.A. (Paris, FRANCE).
 http://www.logilab.fr/ -- mailto:contact@logilab.fr

manipulate pdf and fdf files. pdftk recommended.

Notes regarding pdftk, pdf forms and fdf files (form definition file)
fields names can be extracted with:
    pdftk orig.pdf generate_fdf output truc.fdf
to merge fdf and pdf:
    pdftk orig.pdf fill_form test.fdf output result.pdf [flatten]
without flatten, one could further edit the resulting form.
with flatten, everything is turned into text.
"""

import os
from openerp import tools

HEAD="""%FDF-1.2
%\xE2\xE3\xCF\xD3
1 0 obj
<<
/FDF
<<
/Fields [
"""

TAIL="""]
>>
>>
endobj
trailer

<<
/Root 1 0 R
>>
%%EOF
"""

def output_field(f):
    return "\xfe\xff" + "".join( [ "\x00"+c for c in f ] )

def extract_keys(lines):
    keys = []
    for line in lines:
        if line.startswith('/V'):
            pass
        elif line.startswith('/T'):
            key = line[7:-2]
            key = ''.join(key.split('\x00'))
            keys.append( key )
    return keys

def write_field(out, key, value):
    out.write("<<\n")
    if value:
        out.write("/V (%s)\n" %value)
    else:
        out.write("/V /\n")
    out.write("/T (%s)\n" % output_field(key) )
    out.write(">> \n")

def write_fields(out, fields):
    out.write(HEAD)
    for key in fields:
	    value = fields[key]
	    write_field(out, key, value)
    out.write(TAIL)

def extract_keys_from_pdf(filename):
    # what about using 'pdftk filename dump_data_fields' and parsing the output ?
    os.system('pdftk %s generate_fdf output /tmp/toto.fdf' % filename)
    lines = file('/tmp/toto.fdf').readlines()
    return extract_keys(lines)


def fill_pdf(infile, outfile, fields):
    write_fields(file('/tmp/toto.fdf', 'w'), fields)
    os.system('pdftk %s fill_form /tmp/toto.fdf output %s flatten' % (infile, outfile))

def testfill_pdf(infile, outfile):
    keys = extract_keys_from_pdf(infile)
    fields = []
    for key in keys:
        fields.append( (key, key, '') )
    fill_pdf(infile, outfile, fields)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

