# -*- coding: utf-'8' "-*-"
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

from openerp.osv import osv, fields

import logging

_logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


class PaymentAcquirer(osv.Model):
    _name = 'payment.acquirer'
    _description = 'Payment Acquirer'

    _columns = {
        'name': fields.char('Name', required=True),
        'view_template_id': fields.many2one('ir.ui.view', 'Form Button Template', required=True),
        'env': fields.selection(
            [('test', 'Test'), ('prod', 'Production')],
            string='Environment'),
        'portal_published': fields.boolean('Visible in Portal',
                                           help="Make this payment acquirer available (Customer invoices, etc.)"),
    }

    _defaults = {
        'portal_published': True,
        'env': 'test',
    }

    def _check_required_if_provider(self, cr, uid, ids, context=None):
        for acquirer in self.browse(cr, uid, ids, context=context):
            if any(c for c, f in self._all_columns.items() if getattr(f.column, 'required_if_provider', None) == acquirer.name and not acquirer[c]):
                return False
        return True

    _constraints = [
        (_check_required_if_provider, 'Required fields not filled', ['required for this provider']),
    ]

    def render(self, cr, uid, id, reference, amount, currency, tx_id=None, partner_id=False, partner_values=None, tx_custom_values=None, context=None):
        """ Renders the form template of the given acquirer as a qWeb template.
        All templates should handle:

         - acquirer: the payment.acquirer browse record
         - user: the current user browse record
         - currency: currency browse record
         - amount: amount of the transaction
         - reference: reference of the transaction
         - partner: the current partner browse record, if any (not necessarily set)
         - partner_values: a dictionary of partner-related values
         - tx_custom_values: a dictionary of transaction related values that depends
                             on the acquirer. Some specific keys should be managed
                             in each provider, depending on the features it offers:

          - 'feedback_url': feedback URL, controler that manage answer of the acquirer
                            (without base url)
          - 'return_url': URL for coming back after payment validation (wihout
                          base url)
          - 'cancel_url': URL if the client cancels the payment
          - 'error_url': URL if there is an issue with the payment

         - context: OpenERP context dictionary

        :param string reference: the transaction reference
        :param float amount: the amount the buyer has to pay
        :param res.currency browse record currency: currency
        :param int tx_id: id of a transaction; if set, bypasses all other given
                          values and only render the already-stored transaction
        :param res.partner browse record partner_id: the buyer
        :param dict partner_values: a dictionary of values for the buyer (see above)
        :param dict tx_custom_values: a dictionary of values for the transction
                                      that is given to the acquirer-specific method
                                      generating the form values
        :param dict context: OpenERP context
        """
        if context is None:
            context = {}
        partner = None
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
        acquirer = self.browse(cr, uid, id, context=context)
        method_name = '%s_form_generate_values' % (acquirer.name)

        tx_values = {}
        if tx_id and hasattr(self.pool['payment.transaction'], method_name):
            method = getattr(self.pool['payment.transaction'], method_name)
            tx_values = method(cr, uid, tx_id, tx_custom_values, context=context)
        elif hasattr(self, method_name):
            method = getattr(self, method_name)
            tx_values = method(cr, uid, id, reference, amount, currency, partner_id, partner_values, tx_custom_values, context=context)

        qweb_context = {
            'acquirer': acquirer,
            'user': self.pool.get("res.users").browse(cr, uid, uid, context=context),
            'reference': reference,
            'amount': amount,
            'currency': currency,
            'partner': partner,
            'partner_values': partner_values,
            'tx_values': tx_values,
            'context': context,
        }
        return self.pool['ir.ui.view'].render(cr, uid, acquirer.view_template_id.id, qweb_context, engine='ir.qweb', context=context)

    def get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        if hasattr(self, '%s_get_form_action_url' % acquirer.name):
            return getattr(self, '%s_get_form_action_url' % acquirer.name)(cr, uid, id, context=context)
        return False


class PaymentTransaction(osv.Model):
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _inherit = ['mail.thread']
    _order = 'id desc'

    _columns = {
        'date_create': fields.datetime('Creation Date', readonly=True, required=True),
        'date_validate': fields.datetime('Validation Date'),
        'acquirer_id': fields.many2one(
            'payment.acquirer', 'Acquirer',
            required=True,
        ),
        'type': fields.selection(
            [('server2server', 'Server To Server'), ('form', 'Form')],
            string='Type', required=True),
        'state': fields.selection(
            [('draft', 'Draft'), ('pending', 'Pending'),
             ('done', 'Done'), ('error', 'Error'),
             ('cancel', 'Canceled')
             ], 'Status', required=True,
            track_visiblity='onchange'),
        'state_message': fields.text('Message',
                                     help='Field used to store error and/or validation messages for information'),
        # link with a record e.g. sale order
        # 'feedback_model': fields.char('Model'),
        # 'feedback_res_id': fields.integer('Res Id'),
        # 'feedback_method': fields.char('Method'),  # use a return url with a dedicated controler ?
        # payment
        'amount': fields.float('Amount', required=True,
                               help='Amount in cents',
                               track_visibility='always'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'reference': fields.char('Order Reference', required=True),
        'name': fields.char('Item name'),
        # duplicate partner / transaction data to store the values at transaction time
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_name': fields.char('Partner Name'),
        'partner_lang': fields.char('Lang'),
        'partner_email': fields.char('Email'),
        'partner_zip': fields.char('Zip'),
        'partner_address': fields.char('Address'),
        'partner_city': fields.char('City'),
        'partner_country_id': fields.many2one('res.country', 'Country'),
        'partner_phone': fields.char('Phone'),
        'partner_reference': fields.char('Buyer Reference'),
    }

    _sql_constraints = [
        ('reference_uniq', 'UNIQUE(reference)', 'The payment transaction reference must be unique!'),
    ]

    _defaults = {
        'date_create': fields.datetime.now,
        'type': 'form',
        'state': 'draft',
        'partner_lang': 'en_US',
    }

    def create(self, cr, uid, values, context=None):
        if not 'name' in values and 'reference' in values:
            values['name'] = values['reference']
        if values.get('partner_id'):  # @TDENOTE: not sure
            values.update(self.on_change_partner_id(cr, uid, None, values.get('partner_id'), context=context)['values'])

        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.pool['payment.acquirer'].browse(cr, uid, values.get('acquirer_id'), context=context)
            custom_method_name = '%s_create' % acquirer.name
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(cr, uid, values, context=context))

        return super(PaymentTransaction, self).create(cr, uid, values, context=context)

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
            values = {
                'partner_name': partner.name,
                'partner_lang': partner.lang,
                'partner_email': partner.email,
                'partner_zip': partner.zip,
                'partner_address': ' '.join((partner.street or '', partner.street2 or '')).strip(),
                'partner_city': partner.city,
                'partner_country_id': partner.country_id.id,
                'partner_phone': partner.phone,
            }
        else:
            values = {
                'partner_name': False,
                'partner_lang': 'en_US',
                'partner_email': False,
                'partner_zip': False,
                'partner_address': False,
                'partner_city': False,
                'partner_country_id': False,
                'partner_phone': False,
            }
        return {'values': values}

    def create_s2s(self, cr, uid, tx_values, cc_values, context=None):
        tx_id = self.create(cr, uid, tx_values, context=context)
        return tx_id
