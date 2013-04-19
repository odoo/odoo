# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013 S.A. <http://openerp.com>
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

from openerp.osv import osv, fields

class res_partner(osv.Model):
    _inherit = 'res.partner'
    
    # indirection to avoid passing a copy of the overridable method when declaring the function field
    _commercial_partner_id = lambda self, *args, **kwargs: self._commercial_partner_compute(*args, **kwargs)

    _commercial_partner_id_store_triggers = {
        'res.partner': (lambda self,cr,uid,ids,context=None: self.search(cr, uid, [('id','child_of',ids)]),
                        ['parent_id', 'is_company'], 10)
    }

    _columns = {
        # make the original field stored, in case it's needed for reporting purposes
        'commercial_partner_id': fields.function(_commercial_partner_id, type='many2one', relation='res.partner', string='Commercial Entity',
                                                 store=_commercial_partner_id_store_triggers)
    }

class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    _columns = {
        'commercial_partner_id': fields.related('partner_id', 'commercial_partner_id', string='Commercial Entity', type='many2one',
                                                relation='res.partner', store=True, readonly=True,
                                                help="The commercial entity that will be used on Journal Entries for this invoice")
    }
