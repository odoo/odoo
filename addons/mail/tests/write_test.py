##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

#
# This module test all RPC methods
#

import xmlrpclib

uid = 1
passwd='admin'
server = 'localhost'
db = 'trunk'

sock = xmlrpclib.ServerProxy('http://'+server+':8069/xmlrpc/object')

def _print_data(data, level=0):
    for d in data:
        print '    '*level, d['id']
        _print_data(d['child_ids'], level+1)

print 'With Domain', [('model','=','mail.group')], 'thread_level'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', False, [('model','=','mail.group')], 1)
_print_data(data)

print 'With Domain', [('model','=','mail.group')], 'no thread_level'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', False, [('model','=','mail.group')], 0)
_print_data(data)


print 'With Domain', [('model','=','mail.group'), ('parent_id','=',False)], 'thread_level=0'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', False, [('model','=','mail.group'), ('parent_id','=',False)], 0)
_print_data(data)

print 'With Domain', [('model','=','mail.group'), ('parent_id','=',False)], 'thread_level=2'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', False, [('model','=','mail.group'), ('parent_id','=',False)], 2)
_print_data(data)

print 'Fixed IDS', [2,3,41,43], 'thread_level'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', [2,3,41,43], [], 1)
_print_data(data)

print 'Fixed IDS', [2,43], 'no thread_level'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', [2,43], [], 0)
_print_data(data)

print 'Fixed IDS', [2,43], 'thread_level'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', [2,43], [], 1)
_print_data(data)

print 'domain [id in 3,41]', 'thread_level'
data = sock.execute(db, uid, passwd, 'mail.message', 'message_read', False, [('id','in',[3,41])], 1)
_print_data(data)

