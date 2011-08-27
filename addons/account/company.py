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

from osv import fields, osv

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'overdue_msg': fields.text('Overdue Payments Message', translate=True),
        'property_reserve_and_surplus_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Reserve and Profit/Loss Account",
            view_load=True,
            domain="[('type', '=', 'other')]",
            help="This Account is used for transferring Profit/Loss(If It is Profit: Amount will be added, Loss : Amount will be deducted.), Which is calculated from Profit & Loss Report"),
    }

    _defaults = {
        'overdue_msg': '''Our records indicate that the following payments are still due. If the amount
has already been paid, please disregard this notice. However, if you have any
queries regarding your account, please contact us.
Thank you in advance.
'''
    }

res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
