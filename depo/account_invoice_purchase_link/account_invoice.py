# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Invoice purchase Link module for OpenERP
#    Copyright (C) 2016 MUSTAFA TÜRKER
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

from openerp.osv import orm, fields


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
        # This is the reverse link of the field 'invoice_ids' of sale.order
        # defined in addons/purchase/purchase.py
        'purchase_ids': fields.many2many(
            'purchase.order', 'purchase_invoice_rel', 'invoice_id',
            'purchase_id','Purchase Orders', readonly=True,
            help="This is the list of sale orders related to this invoice."),
        }
