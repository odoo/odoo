# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

class sale_portal_config_settings(osv.TransientModel):
    _inherit = 'account.config.settings'

    _columns = {
        'group_payment_options': fields.boolean('Show payment buttons to employees too',
            implied_group='portal_sale.group_payment_options',
            help="Show online payment options on Sale Orders and Customer Invoices to employees. "
                 "If not checked, these options are only visible to portal users."),
    }