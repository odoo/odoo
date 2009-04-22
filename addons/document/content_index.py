# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution   
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import os
import StringIO
import odt2txt
import tempfile

#
# This should be the indexer
#
def _to_unicode(s):
    try:
        return s.decode('utf-8')
    except UnicodeError:
        try:
            return s.decode('latin')
        except UnicodeError:
            try:
                return s.encode('ascii')
            except UnicodeError:
                return s


def content_index(content, filename=None, content_type=None):
    fname,ext = os.path.splitext(filename)
    result = ''
    if ext in ('.doc'): #or content_type ?
        (stdin,stdout) = os.popen2('antiword -', 'b')
        stdin.write(content)
        stdin.close()
        result = _to_unicode(stdout.read())
    elif ext == '.pdf':
        file_descriptor, file_name = tempfile.mkstemp(suffix=ext)
        os.write(file_descriptor, content)
        os.close(file_descriptor)
        fp = os.popen('pdftotext -enc UTF-8 -nopgbrk '+file_name+' -', 'r')
        result = fp.read()
        fp.close()
    elif ext in ('.xls','.ods','.odt','.odp'):
        s = StringIO.StringIO(content)
        o = odt2txt.OpenDocumentTextFile(s)
        result = _to_unicode(o.toString())
        s.close()
    elif ext in ('.txt','.py','.patch','.html','.csv','.xml'):
        result = content
    else:
        result = content
    return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
