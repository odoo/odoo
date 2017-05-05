# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2011-2013 Akretion
#    @author Sébastien BEAU <sebastien.beau@akretion.com>
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

from openerp import models, fields, api


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    @api.model
    def _get_import_rules(self):
        return [('always', 'Always'),
                ('never', 'Never'),
                ('paid', 'Paid'),
                ('authorized', 'Authorized'),
                ]

    # the logic around the 2 following fields has to be implemented
    # in the connectors (magentoerpconnect, prestashoperpconnect,...)
    days_before_cancel = fields.Integer(
        string='Days before cancel',
        default=30,
        help="After 'n' days, if the 'Import Rule' is not fulfilled, the "
             "import of the sales order will be canceled.",
    )
    import_rule = fields.Selection(selection='_get_import_rules',
                                   string="Import Rule",
                                   default='always',
                                   required=True)

    @api.model
    def get_or_create_payment_method(self, payment_method):
        """ Try to get a payment method or create if it doesn't exist

        :param payment_method: payment method like PayPal, etc.
        :type payment_method: str
        :return: required payment method
        :rtype: recordset
        """
        domain = [('name', '=ilike', payment_method)]
        method = self.search(domain, limit=1)
        if not method:
            method = self.create({'name': payment_method})
        return method
