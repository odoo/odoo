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

#
# This should be the indexer
#
def content_index(content, filename=None, content_type=None):
	fname,ext = os.path.splitext(filename)
	result = ''
	if ext in ('.doc'): #or content_type ?
		(stdin,stdout) = os.popen2('antiword -', 'b')
		stdin.write(content)
		stdin.close()
		result = stdout.read().decode('latin1','replace').encode('utf-8','replace')
	elif ext == '.pdf':
		fname = os.tempnam(filename)+'.pdf'
		fp = file(fname,'wb')
		fp.write(content)
		fp.close()
		fp = os.popen('pdftotext -enc UTF-8 -nopgbrk '+fname+' -', 'r')
		result = fp.read()
		fp.close()
	elif ext in ('.xls','.ods','.odt','.odp'):
		s = StringIO.StringIO(content)
		o = odt2txt.OpenDocumentTextFile(s)
		result = o.toString().encode('ascii','replace')
		s.close()
	elif ext in ('.txt','.py','.patch','.html','.csv','.xml'):
		result = content
	else:
		result = content
	return result