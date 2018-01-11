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

#
# TODO: move this in a YAML test with !python tag
#

import xmlrpclib

DB = 'training3'
USERID = 1
USERPASS = 'admin'


sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % ('localhost',8069))

ids = sock.execute(DB, USERID, USERPASS, 'account.account', 'search', [], {})
account_lists = sock.execute(DB, USERID, USERPASS, 'account.account', 'read', ids, ['parent_id','parent_left','parent_right'])

accounts = dict(map(lambda x: (x['id'],x), account_lists))
for a in account_lists:
    if a['parent_id']:
        assert a['parent_left'] > accounts[a['parent_id'][0]]['parent_left']
        assert a['parent_right'] < accounts[a['parent_id'][0]]['parent_right']
    assert a['parent_left'] < a['parent_right']
    for a2 in account_lists:
        assert not ((a2['parent_right']>a['parent_left']) and 
            (a2['parent_left']<a['parent_left']) and 
            (a2['parent_right']<a['parent_right']))
        if a2['parent_id']==a['id']:
            assert (a2['parent_left']>a['parent_left']) and (a2['parent_right']<a['parent_right'])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
