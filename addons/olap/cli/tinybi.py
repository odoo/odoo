#!/usr/bin/python

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

import optparse

import xmlrpclib
import time

__version__ = '1.0'

parser = optparse.OptionParser(version=__version__)

group = optparse.OptionGroup(parser, "General options")
group.add_option("-c", "--command", dest="command", help="The query to execute")
group.add_option("-s", "--schema", dest="schema", help="The schema to use for the query")
parser.add_option_group(group)

group = optparse.OptionGroup(parser, "Connection options")
group.add_option("-d", "--database", dest="database", help="Database name")
group.add_option("-H", "--hostname", dest="hostname", default='localhost', help="Server hostname")
group.add_option("-U", "--username", dest="username", default='admin', help="Username")
group.add_option("-W", "--password", dest="password", default='admin', help="Password")
group.add_option("-p", "--port", dest="port", default=8069, help="Server port")
parser.add_option_group(group)

(opt, args) = parser.parse_args()

sock = xmlrpclib.ServerProxy('http://'+opt.hostname+':'+str(opt.port)+'/xmlrpc/object')
uid = 1 

axis,data = sock.execute(opt.database, uid, opt.password, 'olap.schema', 'request', opt.schema, opt.command)
COLSPAN = 18
ROWSPAN = 18

print
if len(axis)>1:
    for i in range(8):
        ok = False
        for x in axis[1]:
            if len(x[0])==i:
                ok = True
        if not ok:
            continue
        print ' '*COLSPAN,
        print (('%-'+str(ROWSPAN)+'s ' ) * len(axis[1])) % tuple(map(lambda x: str(len(x[0])==i and x[1] or ''),axis[1]))
for col in data:
    print ('%-'+str(COLSPAN)+'s')% (' '*(len(axis[0][0][0])-1)*2 + str(axis[0].pop(0)[1]),),
    for row in col:
        if row==[False]:
            print ('%-'+str(ROWSPAN)+'s')%('',),
        else:
            print ('%-'+str(ROWSPAN)+'s')%(row,),
    print
print

