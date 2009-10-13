# -*- coding: utf-8 -*-
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
import netsvc
import netsvc
import osv
import time
import pooler

pay_form = '''<?xml version="1.0"?>
<form string="Check payment for buyer">
</form>'''
pay_fields = {
}


pay_form1 = '''<?xml version="1.0"?>
<form string="Check payment for seller">
</form>'''
pay_fields1 = {
}
def _payer(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    pool.get('auction.lots').write(cr,uid,data['ids'],{'is_ok':True, 'state':'paid'})
    return {}


def _payer_sel(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    pool.get('auction.lots').write(cr,uid,data['ids'],{'paid_vnd':True})
    return {}


class wiz_auc_pay(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':pay_form, 'fields': pay_fields, 'state':[('end','Cancel'),('pay','Pay')]}
        },
        'pay': {
        'actions': [_payer],
        'result': {'type': 'state', 'state':'end'}
        }}
wiz_auc_pay('auction.payer')


class wiz_auc_pay_sel(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':pay_form1, 'fields': pay_fields1, 'state':[('end','Cancel'),('pay2','Pay')]}
        },
        'pay2': {
        'actions': [_payer_sel],
        'result': {'type': 'state', 'state':'end'}
        }}
wiz_auc_pay_sel('auction.payer.sel')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

