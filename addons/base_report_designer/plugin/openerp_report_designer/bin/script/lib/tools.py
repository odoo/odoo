# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import urllib

def get_absolute_file_path(url):
    url_unquoted = urllib.unquote(url)
    return os.name == 'nt' and url_unquoted[1:] or url_unquoted 

# This function reads the content of a file and return it to the caller
def read_data_from_file(filename):
    fp = file( filename, "rb" )
    data = fp.read()
    fp.close()
    return data

# This function writes the content to a file
def write_data_to_file(filename, data):
    fp = file( filename, 'wb' )
    fp.write( data )
    fp.close()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
