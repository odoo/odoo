# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
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
from openerp.osv import fields, osv


class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'incoterm_id': fields.many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'intrastat_transaction_id': fields.many2one('l10n_be_intrastat_declaration.transaction', 'Transaction', help="Intrastat nature of transaction"),
        'transport_mode_id': fields.many2one('l10n_be_intrastat_declaration.transport_mode', 'Transport mode'),
        'intrastat_country_id': fields.many2one('res.country', 'Intrastat country', help='Intrastat country, delivery for sales, origin for purchases', domain=[('intrastat','=',True)]),
    }
