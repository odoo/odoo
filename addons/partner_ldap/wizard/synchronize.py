# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

import sys
if sys.version_info[:2] < (2, 4):
    from sets import Set as set

import time
import ldap
import ldap.modlist

import wizard
import pooler

BASE_DN = 'ou=addressbook,dc=localdomain'

def terp2ldap(data):
    res = {}
    for ldap_name, terp in LDAP_TERP_MAPPER.items():
        if callable(terp) and terp(data):
            res[ldap_name] = [terp(data)]
        elif isinstance(terp, basestring) and data[terp]:
            res[ldap_name] = ['%s' % data[terp]]
    return res

def get_lastname(dico):
    lnames = dico['name'].split(' ', 1)[1:]
    if lnames:
        return ' '.join(lnames)
    else:
        return dico['name']

def get_street(dico):
    return ' '.join([dico[x] for x in ('street', 'street2') if dico[x]])

def get_name(attribute):
    def func(dico):
        return dico[attribute][1]
    return func


LDAP_TERP_MAPPER = {
        'displayname': 'name',
        'mail': 'email',
        'o': get_name('partner_id'),
        'telephoneNumber': 'phone',
        'street': get_street,
        'postalcode': 'zip',
        'l': 'city',
        'cn': 'name',
        'sn': get_lastname,
        'uid': 'id',
        }


class sync_ldap(wizard.interface):
    
    _login_arch = '''<?xml version="1.0" ?>
    <form string="LDAP Credentials">
        <field name="ldap_host" colspan="4" />
        <field name="dn" colspan="4" />
        <field name="password" colspan="4" />
    </form>
    '''

    _login_fields = {
            'ldap_host': {'string': 'LDAP Host', 'type': 'char', 'size': 128},
            'dn': {'string': 'Distinguished name', 'type': 'char', 'size': 128},
            'password': {'string': 'Password', 'type': 'char', 'size': 128},
            }

    def _do_sync(self, cr, uid, data, context):
        l = ldap.open(data['form']['ldap_host'])
        l.simple_bind_s(data['form']['dn'], data['form']['password'])
        ldap_objs = dict(l.search_s(BASE_DN, ldap.SCOPE_ONELEVEL, 'objectclass=*',
                                    LDAP_TERP_MAPPER.keys()))
        address = pooler.get_pool(cr.dbname).get('res.partner.address')
        terp_objs = dict([(x['id'], x) for x in address.read(cr, uid, address.search(cr, uid, []))])
        ldap_set = [int(x['uid'][0]) for x in ldap_objs.values()]
        terp_set = terp_objs.keys()
        for to_delete in ldap_set:
            if to_delete in terp_set:
                continue
            l.delete_s('uid=%s,%s' % (to_delete, BASE_DN))
        for to_add in terp_set:
            if to_add in ldap_set:
                continue
            new_dn = 'uid=%s,%s' % (to_add, BASE_DN)
            ldap_data = {'objectclass' : ['organizationalPerson', 'inetOrgPerson']}
            ldap_data.update(terp2ldap(terp_objs[to_add]))
            l.add_s(new_dn, ldap.modlist.addModlist(ldap_data))
            address.write(cr, uid, [to_add], {'dn' : new_dn})
        for to_update in terp_set:
            if to_update not in ldap_set:
                continue
            current_dn = 'uid=%s,%s' % (to_update, BASE_DN)
            modlist = ldap.modlist.modifyModlist(ldap_objs[current_dn], terp2ldap(terp_objs[to_update]))
            if modlist:
                l.modify_s(current_dn, modlist)
        return {}

    states = {
        'init' : {
            'actions' : [],
            'result' : {
                'type' : 'form',
                'arch' : _login_arch,
                'fields' : _login_fields,
                'state' : (('end', 'Cancel'),('sync', 'Synchronize'))
                },
        },
        'sync' : {
            'actions' : [ _do_sync ],
            'result' : { 'type' : 'state', 'state' : 'end' },
        },
    }


sync_ldap('partners.sync_ldap')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

