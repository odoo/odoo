# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Communities Lda (http://www.communities.pt) All Rights Reserved.
#                       João Figueira <jjnf@communities.pt>
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
from openerp.osv import fields, osv
import base64
from openerp.tools.translate import _

#----------------------------------------------------------
# Groups
#----------------------------------------------------------
class radius_groups(osv.osv):
    _name = "radius.groups"
    _description = "Groups"
    _columns = {
        'name': fields.char('Name', size=64, select=1),
    }
radius_groups()

#----------------------------------------------------------
# NAS
#----------------------------------------------------------
class radius_nas(osv.osv):
    _name = "radius.nas"
    _description = "Nas"
    _columns = {
        'nasname': fields.char('Nas IP/Host', size=128, select=1),
        'shortname': fields.char('Nas Shortname', size=32),
#        'type': fields.char('Nas Type', size=32),
        'type': fields.selection([('cisco','cisco'),('portslave','portslave'),('other','other')], 'Nas Type', size=32),
        'ports': fields.integer('Nas Ports'),
        'secret': fields.char('Nas Secret', size=64),
        'community': fields.char('Nas Community', size=64),
        'description': fields.text('Nas Description'),
    }
radius_nas()

#----------------------------------------------------------
# Radacct
#----------------------------------------------------------
class radius_radacct(osv.osv):
    _name = "radius.radacct"
    _description = "Radacct"
    _columns = {
        'name': fields.char('Name', size=64),
        'radacctid': fields.char('Radacctid', size=64),
        'acctsessionid': fields.char('Acctsessionid', size=64),
        'acctuniqueid': fields.char('Acctuniqueid', size=64),
        'username': fields.char('Username', size=128),
        'groupname': fields.char('Group Name', size=128),
        'realm': fields.char('Realm', size=64),
        'nasipaddress': fields.char('Nasipaddress', size=64),
        'nasportid': fields.char('Nasportid', size=64),
        'nasporttype': fields.char('Nasporttype', size=64),
        'acctstarttime': fields.datetime('Acctstarttime'),
        'acctstoptime': fields.datetime('Acctstoptime'),
        'acctsessiontime': fields.float('Acctsessiontime'),
        'acctauthentic': fields.char('Acctauthentic', size=32),
        'connectinfo_start': fields.char('Connectinfo_start', size=64),
        'connectinfo_stop': fields.char('Connectinfo_stop', size=64),
        'acctinputoctets': fields.float('Acctinputoctets'),
        'acctoutputoctets': fields.float('Acctoutputoctets'),
        'calledstationid': fields.char('Calledstationid', size=64),
        'callingstationid': fields.char('Callingstationid', size=64),
        'acctterminatecause': fields.char('Acctterminatecause', size=32),
        'servicetype': fields.char('Servicetype', size=32),
        'xascendsessionsvrkey': fields.char('Xascendsessionsvrkey', size=32),
        'framedprotocol': fields.char('Framedprotocol', size=32),
        'framedipaddress': fields.char('Framedipaddress', size=128),
        'acctstartdelay': fields.integer('Acctstartdelay'),
        'acctstopdelay': fields.integer('Acctstopdelay'),
    }
radius_radacct()

#----------------------------------------------------------
# Radcheck
#----------------------------------------------------------
class radius_radcheck(osv.osv):
    _name = "radius.radcheck"
    _description = "Radcheck"
    _columns = {
        'username': fields.char('Username', size=64, select=1),
#        'attribute': fields.char('Attribute', size=64),
        'attribute': fields.selection([('Cleartext-Password','Cleartext-Password'),('Auth-Type','Auth-Type'),('ChilliSpot-Max-Total-Octets','Quota Attribute'),('ChilliSpot-Max-Total-Gigawords','Quota Gigawords'),('Simultaneous-Use','Simultaneous-Use')], 'Attribute', size=64),        
        'op': fields.selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP'),        
        'value': fields.char('Value', size=253),
    }
radius_radcheck()

#----------------------------------------------------------
# Radreply
#----------------------------------------------------------
class radius_radreply(osv.osv):
    _name = "radius.radreply"
    _description = "Radreply"
    _columns = {
        'username': fields.char('Username', size=64, select=1),
#        'attribute': fields.char('Attribute', size=64),
        'attribute': fields.selection([('Reply-Message','Reply-Message'),('Idle-Timeout','Idle-Timeout'),('Session-Timeout','Session-Timeout'),('WISPr-Redirection-URL','WISPr-Redirection-URL'),('WISPr-Bandwidth-Max-Up','WISPr-Bandwidth-Max-Up'),('WISPr-Bandwidth-Max-Down','WISPr-Bandwidth-Max-Down')], 'Attribute', size=64),
        'op': fields.selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP'),
        'value': fields.char('Value', size=253),
    }
radius_radreply()

#----------------------------------------------------------
# Radgroupcheck
#----------------------------------------------------------
class radius_radgroupcheck(osv.osv):
    _name = "radius.radgroupcheck"
    _description = "Radgroupcheck"
    _columns = {
        'groupname': fields.many2one('radius.groups','Group Name'),
#        'attribute': fields.char('Attribute', size=64),
        'attribute': fields.selection([('Auth-Type','Auth-Type'),('Max-All-Session','Max-All-Session'),('Max-Monthly-Session','Max-Monthly-Session'),('Simultaneous-Use','Simultaneous-Use')], 'Attribute', size=64),
        'op': fields.selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP'),
        'value': fields.char('Value', size=253),
    }
radius_radgroupcheck()

#----------------------------------------------------------
# Radgroupreply
#----------------------------------------------------------
class radius_radgroupreply(osv.osv):
    _name = "radius.radgroupreply"
    _description = "Radgroupreply"
    _columns = {
        'groupname': fields.many2one('radius.groups','Group Name'),
#        'attribute': fields.char('Attribute', size=64),
        'attribute': fields.selection([('Reply-Message','Reply-Message'),('Idle-Timeout','Idle-Timeout'),('Session-Timeout','Session-Timeout'),('WISPr-Redirection-URL','WISPr-Redirection-URL'),('WISPr-Bandwidth-Max-Up','WISPr-Bandwidth-Max-Up'),('WISPr-Bandwidth-Max-Down','WISPr-Bandwidth-Max-Down')], 'Attribute', size=64),
        'op': fields.selection([('=','='),(':=',':='),('==','=='),('+=','+='),('!=','!='),('>','>'),('>=','>='),('<','<'),('<=','<='),('=~','=~')], 'OP'),
        'value': fields.char('Value', size=253),
    }
radius_radgroupreply()

#----------------------------------------------------------
# Radusergroup
#----------------------------------------------------------
class radius_radusergroup(osv.osv):
    _name = "radius.radusergroup"
    _description = "Radusergroup"
    _columns = {
        'username': fields.char('Username', size=64, select=1),
        'groupname': fields.many2one('radius.groups','Group Name'),   
        'priority': fields.integer('priority'),
    }
radius_radusergroup()

#----------------------------------------------------------
# Radpostauth
#----------------------------------------------------------
class radius_radpostauth(osv.osv):
    _name = "radius.radpostauth"
    _description = "radpostauth"
    _columns = {
        'username': fields.char('Username', size=128, select=1),
        'pass': fields.char('Password', size=64),
        'reply': fields.char('Radius Reply', size=64),
        'calledstationid': fields.char('Calledstationid', size=64),
        'callingstationid': fields.char('Callingstationid', size=64),
        'authdate': fields.datetime('Authdate'),
    }
radius_radpostauth()
