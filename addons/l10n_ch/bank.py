# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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

class Bank(osv.osv):
    """Inherit res.bank class in order to add swiss specific field"""
    _inherit = 'res.bank'
    _columns = {
        ###Swiss unik bank identifier also use in IBAN number
        'clearing': fields.char('Clearing number', size=64),
        ### city of the bank
        'city': fields.char('City', size=128, select=1),
    }

Bank()

class bvr_checkbox(osv.osv):
    """ Add function to generate function """
    _inherit = "res.partner.bank"

    _columns = {
        'print_bank' : fields.boolean('Print Bank on BVR'),
        'print_account' : fields.boolean('Print Account Number on BVR'),
        }

bvr_checkbox()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
