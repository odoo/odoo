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

""" This is a testing module, which exports some functions for the YAML tests.
    Instead of repeating the same FTP code all over, we prefer to have
    it in this file
"""

from ftplib import FTP
from tools import config

def get_plain_ftp(timeout=10.0):
    ftp = FTP()
    host = config.get('ftp_server_host', '127.0.0.1')
    port = config.get('ftp_server_port', '8021')
    ftp.connect(host, port,timeout)
    return ftp

def get_ftp_login(cr, uid, ormobj):
    ftp = get_plain_ftp()
    user = ormobj.pool.get('res.users').browse(cr, uid, uid)
    passwd = user.password or ''
    if passwd.startswith("$1$"):
        # md5 by base crypt. We cannot decode, wild guess
        # that passwd = login
        passwd = user.login
    ftp.login(user.login, passwd)
    ftp.cwd("/" + cr.dbname)
    return ftp

def get_ftp_anonymous(cr):
    ftp = get_plain_ftp()
    ftp.login('anonymous', 'the-test')
    ftp.cwd("/")
    return ftp

def get_ftp_folder(cr, uid, ormobj, foldername):
    ftp = get_ftp_login(cr, uid, ormobj)
    ftp.cwd("/" + cr.dbname+"/"+foldername)
    return ftp

def get_ftp_fulldata(ftp, fname, limit=8192):
    from functools import partial
    data = []
    def ffp(data, ndata):
        if len(data)+ len(ndata) > limit:
            raise IndexError('Data over the limit.')
        data.append(ndata)
    ftp.retrbinary('RETR %s' % fname, partial(ffp,data))
    return ''.join(data)

#eof

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
