# -*- coding: utf-'8' "-*-"
import logging

import openerp
from openerp.osv import osv, fields
from openerp.tools import float_round, float_repr, image_get_resized_images, image_resize_image_big
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


def _partner_format_address(address1=False, address2=False):
    return ' '.join((address1 or '', address2 or '')).strip()


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


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
    _order = 'sequence'

    def _get_providers(self, cr, uid, context=None):
        return []

    # indirection to ease inheritance
    _provider_selection = lambda self, *args, **kwargs: self._get_providers(*args, **kwargs)

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'provider': fields.selection(_provider_selection, string='Provider', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'pre_msg': fields.html('Help Message', translate=True,
                               help='Message displayed to explain and help the payment process.'),
        'post_msg': fields.html('Thanks Message', translate=True,
                                help='Message displayed after having done the payment process.'),
        'view_template_id': fields.many2one('ir.ui.view', 'Form Button Template', required=True),
        'registration_view_template_id': fields.many2one('ir.ui.view', 'S2S Form Template',
                                                         domain=[('type', '=', 'qweb')],
                                                         help="Template for method registration"),
        'environment': fields.selection(
            [('test', 'Test'), ('prod', 'Production')],
            string='Environment', oldname='env'),
        'website_published': fields.boolean(
            'Visible in Portal / Website', copy=False,
            help="Make this payment acquirer available (Customer invoices, etc.)"),
        'auto_confirm': fields.selection(
            [('none', 'No automatic confirmation'),
             ('at_pay_confirm', 'At payment with acquirer confirmation'),
             ('at_pay_now', 'At payment no acquirer confirmation needed')],
            string='Order Confirmation', required=True),
        'pending_msg': fields.html('Pending Message', translate=True, help='Message displayed, if order is in pending state after having done the payment process.'),
        'done_msg': fields.html('Done Message', translate=True, help='Message displayed, if order is done successfully after having done the payment process.'),
        'cancel_msg': fields.html('Cancel Message', translate=True, help='Message displayed, if order is cancel during the payment process.'),
        'error_msg': fields.html('Error Message', translate=True, help='Message displayed, if error is occur during the payment process.'),
        # Fees
        'fees_active': fields.boolean('Add Extra Fees'),
        'fees_dom_fixed': fields.float('Fixed domestic fees'),
        'fees_dom_var': fields.float('Variable domestic fees (in percents)'),
        'fees_int_fixed': fields.float('Fixed international fees'),
        'fees_int_var': fields.float('Variable international fees (in percents)'),
        'sequence': fields.integer('Sequence', help="Determine the display order"),
    }

    image = openerp.fields.Binary("Image", attachment=True,
        help="This field holds the image used for this provider, limited to 1024x1024px")
    image_medium = openerp.fields.Binary("Medium-sized image",
        compute='_compute_images', inverse='_inverse_image_medium', store=True, attachment=True,
        help="Medium-sized image of this provider. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = openerp.fields.Binary("Small-sized image",
        compute='_compute_images', inverse='_inverse_image_small', store=True, attachment=True,
        help="Small-sized image of this provider. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    @openerp.api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = openerp.tools.image_resize_image_medium(rec.image)
            rec.image_small = openerp.tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = openerp.tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = openerp.tools.image_resize_image_big(rec.image_small)

    _defaults = {
        'company_id': lambda self, cr, uid, obj, ctx=None: self.pool['res.users'].browse(cr, uid, uid).company_id.id,
        'environment': 'prod',
        'website_published': False,
        'auto_confirm': 'at_pay_confirm',
        'pending_msg': '<i>Pending,</i> Your online payment has been successfully processed. But your order is not validated yet.',
        'done_msg': '<i>Done,</i> Your online payment has been successfully processed. Thank you for your order.',
        'cancel_msg': '<i>Cancel,</i> Your payment has been cancelled.',
        'error_msg': "<i>Error,</i> Please be aware that an error occurred during the transaction. The order has been confirmed but won't be paid. Don't hesitate to contact us if you have any questions on the status of your order."
    }

    def _check_required_if_provider(self, cr, uid, ids, context=None):
        """ If the field has 'required_if_provider="<provider>"' attribute, then it
        required if record.provider is <provider>. """
        for acquirer in self.browse(cr, uid, ids, context=context):
            if any(getattr(f, 'required_if_provider', None) == acquirer.provider and not acquirer[k] for k, f in self._fields.items()):
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

    def render(self, cr, uid, id, reference, amount, currency_id, partner_id=False, values=None, context=None):
        """ Renders the form template of the given acquirer as a qWeb template.
        :param string reference: the transaction reference
        :param float amount: the amount the buyer has to pay
        :param currency_id: currency id
        :param dict partner_id: optional partner_id to fill values
        :param dict values: a dictionary of values for the transction that is
        given to the acquirer-specific method generating the form values
        :param dict context: OpenERP context

        All templates will receive:

         - acquirer: the payment.acquirer browse record
         - user: the current user browse record
         - currency_id: id of the transaction currency
         - amount: amount of the transaction
         - reference: reference of the transaction
         - partner_*: partner-related values
         - partner: optional partner browse record
         - 'feedback_url': feedback URL, controler that manage answer of the acquirer (without base url) -> FIXME
         - 'return_url': URL for coming back after payment validation (wihout base url) -> FIXME
         - 'cancel_url': URL if the client cancels the payment -> FIXME
         - 'error_url': URL if there is an issue with the payment -> FIXME
         - context: OpenERP context dictionary

        """
        if context is None:
            context = {}
        if values is None:
            values = {}
        acquirer = self.browse(cr, uid, id, context=context)

        # reference and amount
        values.setdefault('reference', reference)
        amount = float_round(amount, 2)
        values.setdefault('amount', amount)

        # currency id
        currency_id = values.setdefault('currency_id', currency_id)
        if currency_id:
            currency = self.pool['res.currency'].browse(cr, uid, currency_id, context=context)
        else:
            currency = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.currency_id
        values['currency'] = currency

        # Fill partner_* using values['partner_id'] or partner_id arguement
        partner_id = values.get('partner_id', partner_id)
        billing_partner_id = values.get('billing_partner_id', partner_id)
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
            if partner_id != billing_partner_id:
                billing_partner = self.pool['res.partner'].browse(cr, uid, billing_partner_id, context=context)
            else:
                billing_partner = partner
            values.update({
                'partner': partner,
                'partner_id': partner_id,
                'partner_name': partner.name,
                'partner_lang': partner.lang,
                'partner_email': partner.email,
                'partner_zip': partner.zip,
                'partner_city': partner.city,
                'partner_address': _partner_format_address(partner.street, partner.street2),
                'partner_country_id': partner.country_id.id,
                'partner_country': partner.country_id,
                'partner_phone': partner.phone,
                'partner_state': partner.state_id,
                'billing_partner': billing_partner,
                'billing_partner_id': billing_partner_id,
                'billing_partner_name': billing_partner.name,
                'billing_partner_lang': billing_partner.lang,
                'billing_partner_email': billing_partner.email,
                'billing_partner_zip': billing_partner.zip,
                'billing_partner_city': billing_partner.city,
                'billing_partner_address': _partner_format_address(billing_partner.street, billing_partner.street2),
                'billing_partner_country_id': billing_partner.country_id.id,
                'billing_partner_country': billing_partner.country_id,
                'billing_partner_phone': billing_partner.phone,
                'billing_partner_state': billing_partner.state_id,
            })
        if values.get('partner_name'):
            values.update({
                'partner_first_name': _partner_split_name(values.get('partner_name'))[0],
                'partner_last_name': _partner_split_name(values.get('partner_name'))[1],
            })
        if values.get('billing_partner_name'):
            values.update({
                'billing_partner_first_name': _partner_split_name(values.get('billing_partner_name'))[0],
                'billing_partner_last_name': _partner_split_name(values.get('billing_partner_name'))[1],
            })

        # Fix address, country fields
        if not values.get('partner_address'):
            values['address'] = _partner_format_address(values.get('partner_street', ''), values.get('partner_street2', ''))
        if not values.get('partner_country') and values.get('partner_country_id'):
            values['country'] = self.pool['res.country'].browse(cr, uid, values.get('partner_country_id'), context=context)
        if not values.get('billing_partner_address'):
            values['billing_address'] = _partner_format_address(values.get('billing_partner_street', ''), values.get('billing_partner_street2', ''))
        if not values.get('billing_partner_country') and values.get('billing_partner_country_id'):
            values['billing_country'] = self.pool['res.country'].browse(cr, uid, values.get('billing_partner_country_id'), context=context)


        # compute fees
        fees_method_name = '%s_compute_fees' % acquirer.provider
        if hasattr(self, fees_method_name):
            fees = getattr(self, fees_method_name)(cr, uid, id, values['amount'], values['currency_id'], values['partner_country_id'], context=None)
            values['fees'] = float_round(fees, 2)

        # call <name>_form_generate_values to update the tx dict with acqurier specific values
        cust_method_name = '%s_form_generate_values' % (acquirer.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            values = method(cr, uid, id, values, context=context)

        values.update({
            'tx_url': context.get('tx_url', self.get_form_action_url(cr, uid, id, context=context)),
            'submit_class': context.get('submit_class', 'btn btn-link'),
            'submit_txt': context.get('submit_txt'),
            'acquirer': acquirer,
            'user': self.pool.get("res.users").browse(cr, uid, uid, context=context),
            'context': context,
            'type': values.get('type') or 'form',
        })
        values.setdefault('return_url', False)

        # because render accepts view ids but not qweb -> need to use the xml_id
        return self.pool['ir.ui.view'].render(cr, uid, acquirer.view_template_id.xml_id, values, engine='ir.qweb', context=context)

    def _registration_render(self, cr, uid, id, partner_id, qweb_context=None, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        if qweb_context is None:
            qweb_context = {}
        qweb_context.update(id=id, partner_id=partner_id)
        method_name = '_%s_registration_form_generate_values' % (acquirer.provider,)
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            qweb_context.update(method(cr, uid, id, qweb_context, context=context))
        return self.pool['ir.ui.view'].render(cr, uid, acquirer.registration_view_template_id.xml_id, qweb_context, engine='ir.qweb', context=context)

    def s2s_process(self, cr, uid, id, data, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        cust_method_name = '%s_s2s_form_process' % (acquirer.provider)
        if not self.s2s_validate(cr, uid, id, data, context=context):
            return False
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(cr, uid, data, context=context)
        return True

    def s2s_validate(self, cr, uid, id, data, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        cust_method_name = '%s_s2s_form_validate' % (acquirer.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(cr, uid, id, data, context=context)
        return True


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
    _order = 'id desc'
    _rec_name = 'reference'

    def _lang_get(self, cr, uid, context=None):
        lang_ids = self.pool['res.lang'].search(cr, uid, [], context=context)
        languages = self.pool['res.lang'].browse(cr, uid, lang_ids, context=context)
        return [(language.code, language.name) for language in languages]

    def _default_partner_country_id(self, cr, uid, context=None):
        comp = self.pool['res.company'].browse(cr, uid, context.get('company_id', 1), context=context)
        return comp.country_id.id

    _columns = {
        'create_date': fields.datetime('Creation Date', readonly=True),
        'date_validate': fields.datetime('Validation Date'),
        'acquirer_id': fields.many2one(
            'payment.acquirer', 'Acquirer',
            required=True,
        ),
        'type': fields.selection(
            [('server2server', 'Server To Server'), ('form', 'Form'), ('form_save', 'Form with credentials storage')],
            string='Type', required=True),
        'state': fields.selection(
            [('draft', 'Draft'), ('pending', 'Pending'),
             ('done', 'Done'), ('error', 'Error'),
             ('cancel', 'Canceled')
             ], 'Status', required=True,
            track_visibility='onchange', copy=False),
        'state_message': fields.text('Message',
                                     help='Field used to store error and/or validation messages for information'),
        # payment
        'amount': fields.float('Amount', required=True,
                               digits=(16, 2),
                               track_visibility='always',
                               help='Amount'),
        'fees': fields.float('Fees',
                             digits=(16, 2),
                             track_visibility='always',
                             help='Fees amount; set by the system because depends on the acquirer'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'reference': fields.char('Reference', required=True, help='Internal reference of the TX'),
        'acquirer_reference': fields.char('Acquirer Reference',
                                          help='Reference of the TX as stored in the acquirer database'),
        # duplicate partner / transaction data to store the values at transaction time
        'partner_id': fields.many2one('res.partner', 'Partner', track_visibility='onchange',),
        'partner_name': fields.char('Partner Name'),
        'partner_lang': fields.selection(_lang_get, 'Language'),
        'partner_email': fields.char('Email'),
        'partner_zip': fields.char('Zip'),
        'partner_address': fields.char('Address'),
        'partner_city': fields.char('City'),
        'partner_country_id': fields.many2one('res.country', 'Country', required=True),
        'partner_phone': fields.char('Phone'),
        'html_3ds': fields.char('3D Secure HTML'),

        'callback_eval': fields.char('S2S Callback', help="""\
            Will be safe_eval with `self` being the current transaction. i.e.:
                self.env['my.model'].payment_validated(self)""", oldname="s2s_cb_eval"),
        'payment_method_id': fields.many2one('payment.method', 'Payment Method', domain="[('acquirer_id', '=', acquirer_id)]"),
    }

    def _check_reference(self, cr, uid, ids, context=None):
        transaction = self.browse(cr, uid, ids[0], context=context)
        if transaction.state not in ['cancel', 'error']:
            if self.search(cr, uid, [('reference', '=', transaction.reference), ('id', '!=', transaction.id)], context=context, count=True):
                return False
        return True

    _constraints = [
        (_check_reference, 'The payment transaction reference must be unique!', ['reference', 'state']),
    ]

    _defaults = {
        'type': 'form',
        'state': 'draft',
        'partner_lang': 'en_US',
        'partner_country_id': _default_partner_country_id,
        'reference': lambda s, c, u, ctx=None: s.pool['ir.sequence'].next_by_code(c, u, 'payment.transaction', context=ctx),
    }

    def create(self, cr, uid, values, context=None):
        Acquirer = self.pool['payment.acquirer']

        if values.get('partner_id'):  # @TDENOTE: not sure
            values.update(self.on_change_partner_id(cr, uid, None, values.get('partner_id'), context=context)['value'])

        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.pool['payment.acquirer'].browse(cr, uid, values.get('acquirer_id'), context=context)

            # compute fees
            custom_method_name = '%s_compute_fees' % acquirer.provider
            if hasattr(Acquirer, custom_method_name):
                fees = getattr(Acquirer, custom_method_name)(
                    cr, uid, acquirer.id, values.get('amount', 0.0), values.get('currency_id'), values.get('partner_country_id'), context=None)
                values['fees'] = float_round(fees, 2)

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(cr, uid, values, context=context))

        # Default value of reference is
        tx_id = super(PaymentTransaction, self).create(cr, uid, values, context=context)
        if not values.get('reference'):
            self.write(cr, uid, [tx_id], {'reference': str(tx_id)}, context=context)
        return tx_id

    def write(self, cr, uid, ids, values, context=None):
        Acquirer = self.pool['payment.acquirer']
        if ('acquirer_id' in values or 'amount' in values) and 'fees' not in values:
            # The acquirer or the amount has changed, and the fees are not explicitely forced. Fees must be recomputed.
            if isinstance(ids, (int, long)):
                ids = [ids]
            for txn_id in ids:
                vals = dict(values)
                vals['fees'] = 0.0
                transaction = self.browse(cr, uid, txn_id, context=context)
                if 'acquirer_id' in values:
                    acquirer = Acquirer.browse(cr, uid, values['acquirer_id'], context=context) if values['acquirer_id'] else None
                else:
                    acquirer = transaction.acquirer_id
                if acquirer:
                    custom_method_name = '%s_compute_fees' % acquirer.provider
                    if hasattr(Acquirer, custom_method_name):
                        amount = (values['amount'] if 'amount' in values else transaction.amount) or 0.0
                        currency_id = values.get('currency_id') or transaction.currency_id.id
                        country_id = values.get('partner_country_id') or transaction.partner_country_id.id
                        fees = getattr(Acquirer, custom_method_name)(cr, uid, acquirer.id, amount, currency_id, country_id, context=None)
                        vals['fees'] = float_round(fees, 2)
                res = super(PaymentTransaction, self).write(cr, uid, txn_id, vals, context=context)
            return res
        return super(PaymentTransaction, self).write(cr, uid, ids, values, context=context)

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        partner = None
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
            return {'value': {
                'partner_name': partner and partner.name or False,
                'partner_lang': partner and partner.lang or 'en_US',
                'partner_email': partner and partner.email or False,
                'partner_zip': partner and partner.zip or False,
                'partner_address': _partner_format_address(partner and partner.street or '', partner and partner.street2 or ''),
                'partner_city': partner and partner.city or False,
                'partner_country_id': partner and partner.country_id.id or self._default_partner_country_id(cr, uid, context=context),
                'partner_phone': partner and partner.phone or False,
            }}
        return {}

    def get_next_reference(self, cr, uid, reference, context=None):
        ref_suffix = 1
        init_ref = reference
        while self.pool['payment.transaction'].search_count(cr, openerp.SUPERUSER_ID, [('reference', '=', reference)], context=context):
            reference = init_ref + '-' + str(ref_suffix)
            ref_suffix += 1
        return reference

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def render(self, cr, uid, id, context=None):
        tx = self.browse(cr, uid, id, context=context)
        values = {
            'reference': tx.reference,
            'amount': tx.amount,
            'currency_id': tx.currency_id.id,
            'currency': tx.currency_id,
            'partner': tx.partner_id,
            'partner_name': tx.partner_name,
            'partner_lang': tx.partner_lang,
            'partner_email': tx.partner_email,
            'partner_zip': tx.partner_zip,
            'partner_address': tx.partner_address,
            'partner_city': tx.partner_city,
            'partner_country_id': tx.partner_country_id.id,
            'partner_country': tx.partner_country_id,
            'partner_phone': tx.partner_phone,
            'partner_state': None,
        }
        return tx.acquirer_id.render(None, None, None, values=values)

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

    def s2s_do_transaction(self, cr, uid, id, context=None, **kwargs):
        tx = self.browse(cr, uid, id, context=context)
        custom_method_name = '%s_s2s_do_transaction' % tx.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(cr, uid, id, context=context, **kwargs)

    def s2s_get_tx_status(self, cr, uid, tx_id, context=None):
        """ Get the tx status. """
        tx = self.browse(cr, uid, tx_id, context=context)

        invalid_param_method_name = '_%s_s2s_get_tx_status' % tx.acquirer_id.provider
        if hasattr(self, invalid_param_method_name):
            return getattr(self, invalid_param_method_name)(cr, uid, tx, context=context)

        return True


class PaymentMethod(osv.Model):
    _name = 'payment.method'
    _order = 'partner_id'

    _columns = {
        'name': fields.char('Name', help='Name of the payment method'),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'acquirer_id': fields.many2one('payment.acquirer', 'Acquirer Account', required=True),
        'acquirer_ref': fields.char('Acquirer Ref.', required=True),
        'active': fields.boolean('Active'),
        'payment_ids': fields.one2many('payment.transaction', 'payment_method_id', 'Payment Transactions'),
    }

    _defaults = {
        'active': True
    }

    def create(self, cr, uid, values, context=None):
        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.pool['payment.acquirer'].browse(cr, uid, values.get('acquirer_id'), context=context)

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(cr, uid, values, context=context))

        return super(PaymentMethod, self).create(cr, uid, values, context=context)
