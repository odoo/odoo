# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

from __future__ import with_statement

import os
import tempfile


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
            pass #print 'value',line
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
#        write_field(out, key+"a", value) # pour copie-carbone sur autres pages
    out.write(TAIL)

def extract_keys_from_pdf(filename):
    # what about using 'pdftk filename dump_data_fields' and parsing the output ?
    tmp_file = tempfile.mkstemp(".fdf")[1]
    try:
        os.system('pdftk %s generate_fdf output \"%s\"' % (filename, tmp_file))
        with open(tmp_file, "r") as ofile:
            lines = ofile.readlines()
    finally:
        try:
            os.remove(tmp_file)
        except Exception:
            pass # nothing to do
    return extract_keys(lines)


def fill_pdf(infile, outfile, fields):
    tmp_file = tempfile.mkstemp(".fdf")[1]
    try:
        with open(tmp_file, "w") as ofile:
            write_fields(ofile, fields)
        os.system('pdftk %s fill_form \"%s\" output %s flatten' % (infile, tmp_file, outfile))
    finally:
        try:
            os.remove(tmp_file)
        except Exception:
            pass # nothing to do

def testfill_pdf(infile, outfile):
    keys = extract_keys_from_pdf(infile)
    fields = []
    for key in keys:
        fields.append( (key, key, '') )
    fill_pdf(infile, outfile, fields)
