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


class type(osv.Model):
    _name = 'payment.acquirer.type'
    _columns = {
        'name': fields.char('Name', required=True),
    }


class acquirer(osv.Model):
    _name = 'payment.acquirer'
    _description = 'Online Payment Acquirer'
    
    _columns = {
        'name': fields.char('Name', required=True),
        'type_id': fields.many2one('payment.acquirer.type', required=True),
        'form_template_id': fields.many2one('ir.ui.view', translate=True, required=True), 
        'visible': fields.boolean('Visible', help="Make this payment acquirer available (Customer invoices, etc.)"),
    }

    _defaults = {
        'visible': True,
    }

    def render(self, cr, uid, ids, object, reference, currency, amount, context=None):
        """ Renders the form template of the given acquirer as a qWeb template  """
        view = self.pool.get("ir.ui.view")
        user = self.pool.get("res.users")
        precision = self.pool.get("decimal.precision").precision_get(cr, uid, 'Account')

        qweb_context = {}
        qweb_context.update(
            object=object,
            reference=reference,
            currency=currency,
            amount=amount,
            amount_str=float_repr(amount, precision),
            user_id=user.browse(cr, uid, uid),
            context=context
        )

        res = []
        for pay in self.browse(cr, uid, ids, context=context):
            res[pay.id] = view.render(cr, uid, pay.form_template_id.id, qweb_context.copy(), context=context)
        return res

    def validate_payement(self, cr, uid, ids, object, reference, currency, amount, context=None):
        res = []
        for pay in self.browse(cr, uid, ids, context=context):
            method = getattr(self, '_validate_payement_%s' % pay.type_id.name)
            res[pay.id] = method(cr, uid, ids, object, reference, currency, amount, context=context)
        return res

    def _validate_payement_paypal(self, cr, uid, ids, object, reference, currency, amount, context=None):
        payment = "pending" # "validated" or "refused" or "pending"
        retry_time = False

        return (payment, retry_time)