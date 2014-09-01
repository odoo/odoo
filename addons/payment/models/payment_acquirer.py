# -*- coding: utf-'8' "-*-"

import logging

from openerp.osv import osv, fields
from openerp.tools import float_round, float_repr
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


def _partner_format_address(address1=False, address2=False):
    return ' '.join((address1 or '', address2 or '')).strip()


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[-1:]), ' '.join(partner_name.split()[:-1])]


class ValidationError(ValueError):
    """ Used for value error when validating transaction data coming from acquirers. """
    pass


class PaymentAcquirer(osv.Model):
    """ Acquirer Model. Each specific acquirer can extend the model by adding
    its own fields, using the acquirer_name as a prefix for the new fields.
    Using the required_if_provider='<name>' attribute on fields it is possible
    to have required fields that depend on a specific acquirer.

    Each acquirer has a link to an ir.ui.view record that is a template of
    a button used to display the payment form. See examples in ``payment_ogone``
    and ``payment_paypal`` modules.

    Methods that should be added in an acquirer-specific implementation:

     - ``<name>_form_generate_values(self, cr, uid, id, reference, amount, currency,
       partner_id=False, partner_values=None, tx_custom_values=None, context=None)``:
       method that generates the values used to render the form button template.
     - ``<name>_get_form_action_url(self, cr, uid, id, context=None):``: method
       that returns the url of the button form. It is used for example in
       ecommerce application, if you want to post some data to the acquirer.
     - ``<name>_compute_fees(self, cr, uid, id, amount, currency_id, country_id,
       context=None)``: computed the fees of the acquirer, using generic fields
       defined on the acquirer model (see fields definition).

    Each acquirer should also define controllers to handle communication between
    OpenERP and the acquirer. It generally consists in return urls given to the
    button form and that the acquirer uses to send the customer back after the
    transaction, with transaction details given as a POST request.
    """
    _name = 'payment.acquirer'
    _description = 'Payment Acquirer'

    def _get_providers(self, cr, uid, context=None):
        return []

    # indirection to ease inheritance
    _provider_selection = lambda self, *args, **kwargs: self._get_providers(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True),
        'provider': fields.selection(_provider_selection, string='Provider', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'pre_msg': fields.html('Message', help='Message displayed to explain and help the payment process.'),
        'post_msg': fields.html('Thanks Message', help='Message displayed after having done the payment process.'),
        'validation': fields.selection(
            [('manual', 'Manual'), ('automatic', 'Automatic')],
            string='Process Method',
            help='Static payments are payments like transfer, that require manual steps.'),
        'view_template_id': fields.many2one('ir.ui.view', 'Form Button Template', required=True),
        'environment': fields.selection(
            [('test', 'Test'), ('prod', 'Production')],
            string='Environment', oldname='env'),
        'website_published': fields.boolean(
            'Visible in Portal / Website', copy=False,
            help="Make this payment acquirer available (Customer invoices, etc.)"),
        # Fees
        'fees_active': fields.boolean('Compute fees'),
        'fees_dom_fixed': fields.float('Fixed domestic fees'),
        'fees_dom_var': fields.float('Variable domestic fees (in percents)'),
        'fees_int_fixed': fields.float('Fixed international fees'),
        'fees_int_var': fields.float('Variable international fees (in percents)'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, obj, ctx=None: self.pool['res.users'].browse(cr, uid, uid).company_id.id,
        'environment': 'test',
        'validation': 'automatic',
        'website_published': True,
    }

    def _check_required_if_provider(self, cr, uid, ids, context=None):
        """ If the field has 'required_if_provider="<provider>"' attribute, then it
        required if record.provider is <provider>. """
        for acquirer in self.browse(cr, uid, ids, context=context):
            if any(c for c, f in self._all_columns.items() if getattr(f.column, 'required_if_provider', None) == acquirer.provider and not acquirer[c]):
                return False
        return True

    _constraints = [
        (_check_required_if_provider, 'Required fields not filled', ['required for this provider']),
    ]

    def get_form_action_url(self, cr, uid, id, context=None):
        """ Returns the form action URL, for form-based acquirer implementations. """
        acquirer = self.browse(cr, uid, id, context=context)
        if hasattr(self, '%s_get_form_action_url' % acquirer.provider):
            return getattr(self, '%s_get_form_action_url' % acquirer.provider)(cr, uid, id, context=context)
        return False

    def form_preprocess_values(self, cr, uid, id, reference, amount, currency_id, tx_id, partner_id, partner_values, tx_values, context=None):
        """  Pre process values before giving them to the acquirer-specific render
        methods. Those methods will receive:

             - partner_values: will contain name, lang, email, zip, address, city,
               country_id (int or False), country (browse or False), phone, reference
             - tx_values: will contain refernece, amount, currency_id (int or False),
               currency (browse or False), partner (browse or False)
        """
        acquirer = self.browse(cr, uid, id, context=context)

        if tx_id:
            tx = self.pool.get('payment.transaction').browse(cr, uid, tx_id, context=context)
            tx_data = {
                'reference': tx.reference,
                'amount': tx.amount,
                'currency_id': tx.currency_id.id,
                'currency': tx.currency_id,
                'partner': tx.partner_id,
            }
            partner_data = {
                'name': tx.partner_name,
                'lang': tx.partner_lang,
                'email': tx.partner_email,
                'zip': tx.partner_zip,
                'address': tx.partner_address,
                'city': tx.partner_city,
                'country_id': tx.partner_country_id.id,
                'country': tx.partner_country_id,
                'phone': tx.partner_phone,
                'reference': tx.partner_reference,
            }
        else:
            if partner_id:
                partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
                partner_data = {
                    'name': partner.name,
                    'lang': partner.lang,
                    'email': partner.email,
                    'zip': partner.zip,
                    'city': partner.city,
                    'address': _partner_format_address(partner.street, partner.street2),
                    'country_id': partner.country_id.id,
                    'country': partner.country_id,
                    'phone': partner.phone,
                }
            else:
                partner, partner_data = False, {}
            partner_data.update(partner_values)

            if currency_id:
                currency = self.pool['res.currency'].browse(cr, uid, currency_id, context=context)
            else:
                currency = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id
            tx_data = {
                'reference': reference,
                'amount': amount,
                'currency_id': currency.id,
                'currency': currency,
                'partner': partner,
            }

        # update tx values
        tx_data.update(tx_values)

        # update partner values
        if not partner_data.get('address'):
            partner_data['address'] = _partner_format_address(partner_data.get('street', ''), partner_data.get('street2', ''))
        if not partner_data.get('country') and partner_data.get('country_id'):
            partner_data['country'] = self.pool['res.country'].browse(cr, uid, partner_data.get('country_id'), context=context)
        partner_data.update({
            'first_name': _partner_split_name(partner_data['name'])[0],
            'last_name': _partner_split_name(partner_data['name'])[1],
        })

        # compute fees
        fees_method_name = '%s_compute_fees' % acquirer.provider
        if hasattr(self, fees_method_name):
            fees = getattr(self, fees_method_name)(
                cr, uid, id, tx_data['amount'], tx_data['currency_id'], partner_data['country_id'], context=None)
            tx_data['fees'] = float_round(fees, 2)

        return (partner_data, tx_data)

    def render(self, cr, uid, id, reference, amount, currency_id, tx_id=None, partner_id=False, partner_values=None, tx_values=None, context=None):
        """ Renders the form template of the given acquirer as a qWeb template.
        All templates will receive:

         - acquirer: the payment.acquirer browse record
         - user: the current user browse record
         - currency_id: id of the transaction currency
         - amount: amount of the transaction
         - reference: reference of the transaction
         - partner: the current partner browse record, if any (not necessarily set)
         - partner_values: a dictionary of partner-related values
         - tx_values: a dictionary of transaction related values that depends on
                      the acquirer. Some specific keys should be managed in each
                      provider, depending on the features it offers:

          - 'feedback_url': feedback URL, controler that manage answer of the acquirer
                            (without base url) -> FIXME
          - 'return_url': URL for coming back after payment validation (wihout
                          base url) -> FIXME
          - 'cancel_url': URL if the client cancels the payment -> FIXME
          - 'error_url': URL if there is an issue with the payment -> FIXME

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
        if tx_values is None:
            tx_values = {}
        if partner_values is None:
            partner_values = {}
        acquirer = self.browse(cr, uid, id, context=context)

        # pre-process values
        amount = float_round(amount, 2)
        partner_values, tx_values = self.form_preprocess_values(
            cr, uid, id, reference, amount, currency_id, tx_id, partner_id,
            partner_values, tx_values, context=context)

        # call <name>_form_generate_values to update the tx dict with acqurier specific values
        cust_method_name = '%s_form_generate_values' % (acquirer.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            partner_values, tx_values = method(cr, uid, id, partner_values, tx_values, context=context)

        qweb_context = {
            'tx_url': context.get('tx_url', self.get_form_action_url(cr, uid, id, context=context)),
            'submit_class': context.get('submit_class', 'btn btn-link'),
            'submit_txt': context.get('submit_txt'),
            'acquirer': acquirer,
            'user': self.pool.get("res.users").browse(cr, uid, uid, context=context),
            'reference': tx_values['reference'],
            'amount': tx_values['amount'],
            'currency': tx_values['currency'],
            'partner': tx_values.get('partner'),
            'partner_values': partner_values,
            'tx_values': tx_values,
            'context': context,
        }

        # because render accepts view ids but not qweb -> need to use the xml_id
        return self.pool['ir.ui.view'].render(cr, uid, acquirer.view_template_id.xml_id, qweb_context, engine='ir.qweb', context=context)

    def _wrap_payment_block(self, cr, uid, html_block, amount, currency_id, context=None):
        payment_header = _('Pay safely online')
        amount_str = float_repr(amount, self.pool.get('decimal.precision').precision_get(cr, uid, 'Account'))
        currency = self.pool['res.currency'].browse(cr, uid, currency_id, context=context)
        currency_str = currency.symbol or currency.name
        amount = u"%s %s" % ((currency_str, amount_str) if currency.position == 'before' else (amount_str, currency_str))
        result = u"""<div class="payment_acquirers">
                         <div class="payment_header">
                             <div class="payment_amount">%s</div>
                             %s
                         </div>
                         %%s
                     </div>""" % (amount, payment_header)
        return result % html_block.decode("utf-8")

    def render_payment_block(self, cr, uid, reference, amount, currency_id, tx_id=None, partner_id=False, partner_values=None, tx_values=None, company_id=None, context=None):
        html_forms = []
        domain = [('website_published', '=', True), ('validation', '=', 'automatic')]
        if company_id:
            domain.append(('company_id', '=', company_id))
        acquirer_ids = self.search(cr, uid, domain, context=context)
        for acquirer_id in acquirer_ids:
            button = self.render(
                cr, uid, acquirer_id,
                reference, amount, currency_id,
                tx_id, partner_id, partner_values, tx_values,
                context)
            html_forms.append(button)
        if not html_forms:
            return ''
        html_block = '\n'.join(filter(None, html_forms))
        return self._wrap_payment_block(cr, uid, html_block, amount, currency_id, context=context)


class PaymentTransaction(osv.Model):
    """ Transaction Model. Each specific acquirer can extend the model by adding
    its own fields.

    Methods that can be added in an acquirer-specific implementation:

     - ``<name>_create``: method receiving values used when creating a new
       transaction and that returns a dictionary that will update those values.
       This method can be used to tweak some transaction values.

    Methods defined for convention, depending on your controllers:

     - ``<name>_form_feedback(self, cr, uid, data, context=None)``: method that
       handles the data coming from the acquirer after the transaction. It will
       generally receives data posted by the acquirer after the transaction.
    """
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _rec_name = 'reference'

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
            track_visiblity='onchange', copy=False),
        'state_message': fields.text('Message',
                                     help='Field used to store error and/or validation messages for information'),
        # payment
        'amount': fields.float('Amount', required=True,
                               digits=(16, 2),
                               track_visibility='always',
                               help='Amount in cents'),
        'fees': fields.float('Fees',
                             digits=(16, 2),
                             track_visibility='always',
                             help='Fees amount; set by the system because depends on the acquirer'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'reference': fields.char('Order Reference', required=True),
        'acquirer_reference': fields.char('Acquirer Order Reference',
                                          help='Reference of the TX as stored in the acquirer database'),
        # duplicate partner / transaction data to store the values at transaction time
        'partner_id': fields.many2one('res.partner', 'Partner', track_visibility='onchange',),
        'partner_name': fields.char('Partner Name'),
        'partner_lang': fields.char('Lang'),
        'partner_email': fields.char('Email'),
        'partner_zip': fields.char('Zip'),
        'partner_address': fields.char('Address'),
        'partner_city': fields.char('City'),
        'partner_country_id': fields.many2one('res.country', 'Country', required=True),
        'partner_phone': fields.char('Phone'),
        'partner_reference': fields.char('Partner Reference',
                                         help='Reference of the customer in the acquirer database'),
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
        Acquirer = self.pool['payment.acquirer']

        if values.get('partner_id'):  # @TDENOTE: not sure
            values.update(self.on_change_partner_id(cr, uid, None, values.get('partner_id'), context=context)['values'])

        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.pool['payment.acquirer'].browse(cr, uid, values.get('acquirer_id'), context=context)

            # compute fees
            custom_method_name = '%s_compute_fees' % acquirer.provider
            if hasattr(Acquirer, custom_method_name):
                fees = getattr(Acquirer, custom_method_name)(
                    cr, uid, acquirer.id, values.get('amount', 0.0), values.get('currency_id'), values.get('country_id'), context=None)
                values['fees'] = float_round(fees, 2)

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(cr, uid, values, context=context))

        return super(PaymentTransaction, self).create(cr, uid, values, context=context)

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        partner = None
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
        return {'values': {
            'partner_name': partner and partner.name or False,
            'partner_lang': partner and partner.lang or 'en_US',
            'partner_email': partner and partner.email or False,
            'partner_zip': partner and partner.zip or False,
            'partner_address': _partner_format_address(partner and partner.street or '', partner and partner.street2 or ''),
            'partner_city': partner and partner.city or False,
            'partner_country_id': partner and partner.country_id.id or False,
            'partner_phone': partner and partner.phone or False,
        }}

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def form_feedback(self, cr, uid, data, acquirer_name, context=None):
        invalid_parameters, tx = None, None

        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(cr, uid, data, context=context)

        invalid_param_method_name = '_%s_form_get_invalid_parameters' % acquirer_name
        if hasattr(self, invalid_param_method_name):
            invalid_parameters = getattr(self, invalid_param_method_name)(cr, uid, tx, data, context=context)

        if invalid_parameters:
            _error_message = '%s: incorrect tx data:\n' % (acquirer_name)
            for item in invalid_parameters:
                _error_message += '\t%s: received %s instead of %s\n' % (item[0], item[1], item[2])
            _logger.error(_error_message)
            return False

        feedback_method_name = '_%s_form_validate' % acquirer_name
        if hasattr(self, feedback_method_name):
            return getattr(self, feedback_method_name)(cr, uid, tx, data, context=context)

        return True

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    def s2s_create(self, cr, uid, values, cc_values, context=None):
        tx_id, tx_result = self.s2s_send(cr, uid, values, cc_values, context=context)
        self.s2s_feedback(cr, uid, tx_id, tx_result, context=context)
        return tx_id

    def s2s_send(self, cr, uid, values, cc_values, context=None):
        """ Create and send server-to-server transaction.

        :param dict values: transaction values
        :param dict cc_values: credit card values that are not stored into the
                               payment.transaction object. Acquirers should
                               handle receiving void or incorrect cc values.
                               Should contain :

                                - holder_name
                                - number
                                - cvc
                                - expiry_date
                                - brand
                                - expiry_date_yy
                                - expiry_date_mm
        """
        tx_id, result = None, None

        if values.get('acquirer_id'):
            acquirer = self.pool['payment.acquirer'].browse(cr, uid, values.get('acquirer_id'), context=context)
            custom_method_name = '_%s_s2s_send' % acquirer.provider
            if hasattr(self, custom_method_name):
                tx_id, result = getattr(self, custom_method_name)(cr, uid, values, cc_values, context=context)

        if tx_id is None and result is None:
            tx_id = super(PaymentTransaction, self).create(cr, uid, values, context=context)
        return (tx_id, result)

    def s2s_feedback(self, cr, uid, tx_id, data, context=None):
        """ Handle the feedback of a server-to-server transaction. """
        tx = self.browse(cr, uid, tx_id, context=context)
        invalid_parameters = None

        invalid_param_method_name = '_%s_s2s_get_invalid_parameters' % tx.acquirer_id.provider
        if hasattr(self, invalid_param_method_name):
            invalid_parameters = getattr(self, invalid_param_method_name)(cr, uid, tx, data, context=context)

        if invalid_parameters:
            _error_message = '%s: incorrect tx data:\n' % (tx.acquirer_id.name)
            for item in invalid_parameters:
                _error_message += '\t%s: received %s instead of %s\n' % (item[0], item[1], item[2])
            _logger.error(_error_message)
            return False

        feedback_method_name = '_%s_s2s_validate' % tx.acquirer_id.provider
        if hasattr(self, feedback_method_name):
            return getattr(self, feedback_method_name)(cr, uid, tx, data, context=context)

        return True

    def s2s_get_tx_status(self, cr, uid, tx_id, context=None):
        """ Get the tx status. """
        tx = self.browse(cr, uid, tx_id, context=context)

        invalid_param_method_name = '_%s_s2s_get_tx_status' % tx.acquirer_id.provider
        if hasattr(self, invalid_param_method_name):
            return getattr(self, invalid_param_method_name)(cr, uid, tx, context=context)

        return True
