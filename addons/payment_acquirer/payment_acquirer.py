# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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

import openerp
from openerp.osv import osv, fields
from openerp.tools import float_repr
import urlparse
import requests
import logging

_logger = logging.getLogger(__name__)

class type(osv.osv):
    _name = 'payment.acquirer.type'
    _columns = {
        'name': fields.char('Name', required=True),
    }
    def validate_payement(self, cr, uid, id, object, reference, currency, amount, context=None):
        """
        return (payment, retry_time)
            payment: "validated" or "refused" or "pending"
            retry_time = False (don't retry validation) or int (seconds for retry validation)
        """
        if isinstance(id, list):
            id = id[0]
        pay_type = self.browse(cr, uid, id, context=context)
        method = getattr(self, '_validate_payement_%s' % pay_type.name)
        return method(object, reference, currency, amount, context=context)

    def _validate_payement_virement(self, object, reference, currency, amount, context=None):
        return ("pending", False)


class type_paypal(osv.osv):
    _inherit = "payment.acquirer.type"

    def _validate_payement_paypal(self, object, reference, currency, amount, context=None):
        parameters = {}
        parameters.update(
            cmd='_notify-validate',
            business=object.company_id.paypal_account,
            item_name="%s %s" % (object.company_id.name, reference),
            item_number=reference,
            amount=amount,
            currency_code=currency.name
        )
        paypal_url = "https://www.paypal.com/cgi-bin/webscr"
        paypal_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
        response = urlparse.parse_qsl(requests.post(paypal_url, data=parameters))

        # transaction's unique id
        # response["txn_id"]

        if response["payment_status"] == "Voided":
            raise "Paypal authorization has been voided."
        elif response["payment_status"] in ("Completed", "Processed") and response["item_number"] == reference and response["mc_gross"] == amount:
            return ("validated", False)
        elif response["payment_status"] == "Expired":
            _logger.warn("Paypal Validate Payement status: Expired")
            return ("pending", 5)
        elif response["payment_status"] == "Pending":
            _logger.warn("Paypal Validate Payement status: Pending, reason: %s" % response["pending_reason"])
            return ("pending", 5)

        # Canceled_Reversal, Denied, Failed, Refunded, Reversed
        return ("refused", False)


class acquirer(osv.osv):
    _name = 'payment.acquirer'
    _description = 'Online Payment Acquirer'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'type_id': fields.many2one('payment.acquirer.type', required=True),
        'form_template_id': fields.many2one('ir.ui.view', required=True), 
        'visible': fields.boolean('Visible', help="Make this payment acquirer available (Customer invoices, etc.)"),
    }

    _defaults = {
        'visible': True,
    }

    def render(self, cr, uid, id, object, reference, currency, amount, cancel_url=None, return_url=None, context=None):
        """ Renders the form template of the given acquirer as a qWeb template  """
        user = self.pool.get("res.users")
        precision = self.pool.get("decimal.precision").precision_get(cr, openerp.SUPERUSER_ID, 'Account')

        if not context:
            context = {}

        qweb_context = {}
        qweb_context.update(
            object=object,
            reference=reference,
            currency=currency,
            amount=amount,
            amount_str=float_repr(amount, precision),
            user_id=user.browse(cr, uid, uid),
            context=context,
            cancel_url=cancel_url,
            return_url=return_url
        )

        return self.browse(cr, uid, id, context=context) \
            .form_template_id.render(qweb_context, engine='ir.qweb', context=context) \
            .strip()

    def validate_payement(self, cr, uid, id, object, reference, currency, amount, context=None):
        """
        return (payment, retry_time)
            payment: "validated" or "refused" or "pending"
            retry_time = False (don't retry validation) or int (seconds for retry validation)
        """
        if isinstance(id, list):
            id = id[0]
        type_id = self.browse(cr, uid, id, context=context).type_id
        return type_id.validate_payement(object, reference, currency, amount, context=context)
