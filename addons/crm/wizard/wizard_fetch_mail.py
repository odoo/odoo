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
import wizard
import time
import pooler
import tools
import os
_email_form = '''<?xml version="1.0"?>
<form string="Email Gateway">
    <label string="Fetch Email from Email Gate Way" />
 </form>'''

_email_fields = {
       }

def fetch_mail(self , cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    gateway_pool=pool.get('crm.email.gateway')
    gateway_pool.fetch_mail(cr, uid, data['ids'], context=context)
    return {}

class wiz_fetch_mail(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_email_form, 'fields':_email_fields, 'state':[('run','Run','gtk-execute'),('end','Cancel','gtk-cancel')]}
                },
        'run': {
            'actions': [fetch_mail],
            'result': {'type': 'state', 'state': 'end'}
                },
    }
wiz_fetch_mail('crm.case.section.fetchmail')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
