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

import math
from osv import osv
from tools.misc import UpdateableStr
import pooler

class partner_wizard_ean_check(osv.osv_memory):
    """ Ean check """

    _name = "partner.wizard.ean.check"
    _description = "Ean Check"

    def is_pair(x):
        return not x%2

    def get_ean_key(string):
        if not string or string=='':
            return '0'
        if len(string)!=12:
            return '0'
        sum = 0
        for i in range(12):
            if is_pair(i):
                sum = sum + int(string[i])
            else:
                sum = sum + 3*int(string[i])
        return str(int(math.ceil(sum/10.0)*10-sum))

    def default_get(self, cr, fields, context):
        partner_table = self.pool.get('res.partner')
        ids = context.get('active_ids')
        partners = partner_table.browse(cr, uid, ids)
        _check_arch_lst = ['<?xml version="1.0"?>', '<form string="Check EAN13">', '<label string=""/>', '<label string=""/>','<label string="Original" />', '<label string="Computed" />']
        for partner in partners:
            if partner['ean13'] and len(partner['ean13'])>11 and len(partner['ean13'])<14:
                _check_arch_lst.append('<label colspan="2" string="%s" />' % partner['ean13']);
                key = get_ean_key(partner['ean13'][:12])
                _check_arch_lst.append('<label string=""/>')
                if len(partner['ean13'])==12:
                    _check_arch_lst.append('<label string="" />');
                else:
                    _check_arch_lst.append('<label string="%s" />' % partner['ean13'][12])
                _check_arch_lst.append('<label string="%s" />' % key)
        _check_arch_lst.append('</form>')
        _check_arch.string = '\n'.join(_check_arch_lst)

    def update_ean(self, cr, uid, ids, context):
        partner_table = self.pool.get('res.partner')
        ids = context.get('active_ids')
        partners = partner_table.browse(cr, uid, ids)
        for partner in partners:
            partner_table.write(cr, uid, ids, {
                'ean13': "%s%s" % (partner['ean13'][:12], get_ean_key(partner['ean13'][:12]))
            })
        return {}

partner_wizard_ean_check()