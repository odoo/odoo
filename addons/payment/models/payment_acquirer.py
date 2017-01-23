# coding: utf-8
import logging

from odoo import api, exceptions, fields, models, _
from odoo.tools import float_round, image_resize_images
from odoo.addons.base.module import module
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _partner_format_address(address1=False, address2=False):
    return ' '.join((address1 or '', address2 or '')).strip()


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


class PaymentAcquirer(models.Model):
    """ Acquirer Model. Each specific acquirer can extend the model by adding
    its own fields, using the acquirer_name as a prefix for the new fields.
    Using the required_if_provider='<name>' attribute on fields it is possible
    to have required fields that depend on a specific acquirer.

    Each acquirer has a link to an ir.ui.view record that is a template of
    a button used to display the payment form. See examples in ``payment_ogone``
    and ``payment_paypal`` modules.

    Methods that should be added in an acquirer-specific implementation:

     - ``<name>_form_generate_values(self, reference, amount, currency,
       partner_id=False, partner_values=None, tx_custom_values=None)``:
       method that generates the values used to render the form button template.
     - ``<name>_get_form_action_url(self):``: method that returns the url of
       the button form. It is used for example in ecommerce application if you
       want to post some data to the acquirer.
     - ``<name>_compute_fees(self, amount, currency_id, country_id)``: computes
       the fees of the acquirer, using generic fields defined on the acquirer
       model (see fields definition).

    Each acquirer should also define controllers to handle communication between
    OpenERP and the acquirer. It generally consists in return urls given to the
    button form and that the acquirer uses to send the customer back after the
    transaction, with transaction details given as a POST request.
    """
    _name = 'payment.acquirer'
    _description = 'Payment Acquirer'
    _order = 'sequence'

    name = fields.Char('Name', required=True, translate=True)
    description = fields.Html('Description')
    sequence = fields.Integer('Sequence', help="Determine the display order")
    provider = fields.Selection(
        selection=[('manual', 'Manual Configuration')], string='Provider',
        default='manual', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.user.company_id.id, required=True)
    view_template_id = fields.Many2one(
        'ir.ui.view', 'Form Button Template', required=True)
    registration_view_template_id = fields.Many2one(
        'ir.ui.view', 'S2S Form Template', domain=[('type', '=', 'qweb')],
        help="Template for method registration")
    environment = fields.Selection([
        ('test', 'Test'),
        ('prod', 'Production')], string='Environment',
        default='test', oldname='env', required=True)
    website_published = fields.Boolean(
        'Visible in Portal / Website', copy=False,
        help="Make this payment acquirer available (Customer invoices, etc.)")
    auto_confirm = fields.Selection([
        ('none', 'No automatic confirmation'),
        ('authorize', 'Authorize the amount and confirm the SO on acquirer confirmation (capture manually)'),
        ('confirm_so', 'Authorize & capture the amount and confirm the SO on acquirer confirmation'),
        ('generate_and_pay_invoice', 'Authorize & capture the amount, confirm the SO and auto-validate the invoice on acquirer confirmation')],
        string='Order Confirmation', default='confirm_so', required=True)
    journal_id = fields.Many2one(
        'account.journal', 'Payment Journal',
        help="Account journal used for automatic payment reconciliation.")

    pre_msg = fields.Html(
        'Help Message', translate=True,
        help='Message displayed to explain and help the payment process.')
    post_msg = fields.Html(
        'Thanks Message', translate=True,
        help='Message displayed after having done the payment process.')
    pending_msg = fields.Html(
        'Pending Message', translate=True,
        default='<i>Pending,</i> Your online payment has been successfully processed. But your order is not validated yet.',
        help='Message displayed, if order is in pending state after having done the payment process.')
    done_msg = fields.Html(
        'Done Message', translate=True,
        default='<i>Done,</i> Your online payment has been successfully processed. Thank you for your order.',
        help='Message displayed, if order is done successfully after having done the payment process.')
    cancel_msg = fields.Html(
        'Cancel Message', translate=True,
        default='<i>Cancel,</i> Your payment has been cancelled.',
        help='Message displayed, if order is cancel during the payment process.')
    error_msg = fields.Html(
        'Error Message', translate=True,
        default='<i>Error,</i> Please be aware that an error occurred during the transaction. The order has been confirmed but will not be paid. Do not hesitate to contact us if you have any questions on the status of your order.',
        help='Message displayed, if error is occur during the payment process.')
    save_token = fields.Selection([
        ('none', 'Never'),
        ('ask', 'Let the customer decide'),
        ('always', 'Always')],
        string='Store Card Data', default='none',
        help="Determine if card data is saved as a token automatically or not. "
        "Payment tokens allow your customer to reuse their cards in the e-commerce "
        "or allow you to charge an invoice directly on a credit card. If set to "
        "'let the customer decide', ecommerce customers will have a checkbox displayed on the payment page.")
    token_implemented = fields.Boolean('Saving Card Data supported', compute='_compute_feature_support')

    fees_implemented = fields.Boolean('Fees Computation Supported', compute='_compute_feature_support')
    fees_active = fields.Boolean('Add Extra Fees')
    fees_dom_fixed = fields.Float('Fixed domestic fees')
    fees_dom_var = fields.Float('Variable domestic fees (in percents)')
    fees_int_fixed = fields.Float('Fixed international fees')
    fees_int_var = fields.Float('Variable international fees (in percents)')

    # TDE FIXME: remove that brol
    module_id = fields.Many2one('ir.module.module', string='Corresponding Module')
    module_state = fields.Selection(selection=module.STATES, string='Installation State', related='module_id.state')

    image = fields.Binary(
        "Image", attachment=True,
        help="This field holds the image used for this provider, limited to 1024x1024px")
    image_medium = fields.Binary(
        "Medium-sized image", attachment=True,
        help="Medium-sized image of this provider. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized image", attachment=True,
        help="Small-sized image of this provider. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    @api.multi
    def _compute_feature_support(self):
        feature_support = self._get_feature_support()
        for acquirer in self:
            acquirer.fees_implemented = acquirer.provider in feature_support['fees']
            acquirer.token_implemented = acquirer.provider in feature_support['tokenize']

    @api.multi
    def _check_required_if_provider(self):
        """ If the field has 'required_if_provider="<provider>"' attribute, then it
        required if record.provider is <provider>. """
        for acquirer in self:
            if any(getattr(f, 'required_if_provider', None) == acquirer.provider and not acquirer[k] for k, f in self._fields.items()):
                return False
        return True

    @api.constrains('auto_confirm')
    def _check_authorization_support(self):
        for acquirer in self:
            if acquirer.auto_confirm == 'authorize' and acquirer.provider not in self._get_feature_support()['authorize']:
                raise ValidationError('Transaction Authorization is not supported by this payment provider.')
        return True

    _constraints = [
        (_check_required_if_provider, 'Required fields not filled', []),
    ]

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        return dict(authorize=[], tokenize=[], fees=[])

    @api.model
    def create(self, vals):
        image_resize_images(vals)
        return super(PaymentAcquirer, self).create(vals)

    @api.multi
    def write(self, vals):
        image_resize_images(vals)
        return super(PaymentAcquirer, self).write(vals)

    @api.multi
    def get_form_action_url(self):
        """ Returns the form action URL, for form-based acquirer implementations. """
        if hasattr(self, '%s_get_form_action_url' % self.provider):
            return getattr(self, '%s_get_form_action_url' % self.provider)()
        return False

    @api.multi
    def render(self, reference, amount, currency_id, partner_id=False, values=None):
        """ Renders the form template of the given acquirer as a qWeb template.
        :param string reference: the transaction reference
        :param float amount: the amount the buyer has to pay
        :param currency_id: currency id
        :param dict partner_id: optional partner_id to fill values
        :param dict values: a dictionary of values for the transction that is
        given to the acquirer-specific method generating the form values

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
         - context: Odoo context

        """
        if values is None:
            values = {}

        # reference and amount
        values.setdefault('reference', reference)
        amount = float_round(amount, 2)
        values.setdefault('amount', amount)

        # currency id
        currency_id = values.setdefault('currency_id', currency_id)
        if currency_id:
            currency = self.env['res.currency'].browse(currency_id)
        else:
            currency = self.env.user.company_id.currency_id
        values['currency'] = currency

        # Fill partner_* using values['partner_id'] or partner_id argument
        partner_id = values.get('partner_id', partner_id)
        billing_partner_id = values.get('billing_partner_id', partner_id)
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if partner_id != billing_partner_id:
                billing_partner = self.env['res.partner'].browse(billing_partner_id)
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
            values['country'] = self.env['res.country'].browse(values.get('partner_country_id'))
        if not values.get('billing_partner_address'):
            values['billing_address'] = _partner_format_address(values.get('billing_partner_street', ''), values.get('billing_partner_street2', ''))
        if not values.get('billing_partner_country') and values.get('billing_partner_country_id'):
            values['billing_country'] = self.env['res.country'].browse(values.get('billing_partner_country_id'))

        # compute fees
        fees_method_name = '%s_compute_fees' % self.provider
        if hasattr(self, fees_method_name):
            fees = getattr(self, fees_method_name)(values['amount'], values['currency_id'], values.get('partner_country_id'))
            values['fees'] = float_round(fees, 2)

        # call <name>_form_generate_values to update the tx dict with acqurier specific values
        cust_method_name = '%s_form_generate_values' % (self.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            values = method(values)

        values.update({
            'tx_url': self._context.get('tx_url', self.get_form_action_url()),
            'submit_class': self._context.get('submit_class', 'btn btn-link'),
            'submit_txt': self._context.get('submit_txt'),
            'acquirer': self,
            'user': self.env.user,
            'context': self._context,
            'type': values.get('type') or 'form',
        })
        values.setdefault('return_url', False)

        return self.view_template_id.render(values, engine='ir.qweb')

    @api.multi
    def _registration_render(self, partner_id, qweb_context=None):
        if qweb_context is None:
            qweb_context = {}
        qweb_context.update(id=self.ids[0], partner_id=partner_id)
        method_name = '_%s_registration_form_generate_values' % (self.provider,)
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            qweb_context.update(method(qweb_context))
        return self.registration_view_template_id.render(qweb_context, engine='ir.qweb')

    @api.multi
    def s2s_process(self, data):
        cust_method_name = '%s_s2s_form_process' % (self.provider)
        if not self.s2s_validate(data):
            return False
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(data)
        return True

    @api.multi
    def s2s_validate(self, data):
        cust_method_name = '%s_s2s_form_validate' % (self.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(data)
        return True

    @api.multi
    def toggle_enviroment_value(self):
        prod = self.filtered(lambda acquirer: acquirer.environment == 'prod')
        prod.write({'environment': 'test'})
        (self-prod).write({'environment': 'prod'})

    @api.multi
    def button_immediate_install(self):
        # TDE FIXME: remove that brol
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            context = dict(self._context, active_id=self.ids[0])
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.acquirer',
                'type': 'ir.actions.act_window',
                'res_id': self.ids[0],
                'context': context,
            }


class PaymentTransaction(models.Model):
    """ Transaction Model. Each specific acquirer can extend the model by adding
    its own fields.

    Methods that can be added in an acquirer-specific implementation:

     - ``<name>_create``: method receiving values used when creating a new
       transaction and that returns a dictionary that will update those values.
       This method can be used to tweak some transaction values.

    Methods defined for convention, depending on your controllers:

     - ``<name>_form_feedback(self, data)``: method that handles the data coming
       from the acquirer after the transaction. It will generally receives data
       posted by the acquirer after the transaction.
    """
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _order = 'id desc'
    _rec_name = 'reference'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _get_default_partner_country_id(self):
        return self.env['res.company']._company_default_get('payment.transaction').country_id.id

    create_date = fields.Datetime('Creation Date', readonly=True)
    date_validate = fields.Datetime('Validation Date')
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', required=True)
    type = fields.Selection([
        ('server2server', 'Server To Server'),
        ('form', 'Form'),
        ('form_save', 'Form with tokenization')], 'Type',
        default='form', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('cancel', 'Canceled')], 'Status',
        copy=False, default='draft', required=True, track_visibility='onchange')
    state_message = fields.Text('Message', help='Field used to store error and/or validation messages for information')
    # payment
    amount = fields.Float(
        'Amount', digits=(16, 2), required=True, track_visibility='always',
        help='Amount')
    fees = fields.Float(
        'Fees', digits=(16, 2), track_visibility='always',
        help='Fees amount; set by the system because depends on the acquirer')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    reference = fields.Char(
        'Reference', default=lambda self: self.env['ir.sequence'].next_by_code('payment.transaction'),
        required=True, help='Internal reference of the TX')
    acquirer_reference = fields.Char('Acquirer Reference', help='Reference of the TX as stored in the acquirer database')
    # duplicate partner / transaction data to store the values at transaction time
    partner_id = fields.Many2one('res.partner', 'Partner', track_visibility='onchange')
    partner_name = fields.Char('Partner Name')
    partner_lang = fields.Selection(_lang_get, 'Language', default=lambda self: self.env.lang)
    partner_email = fields.Char('Email')
    partner_zip = fields.Char('Zip')
    partner_address = fields.Char('Address')
    partner_city = fields.Char('City')
    partner_country_id = fields.Many2one('res.country', 'Country', default=_get_default_partner_country_id, required=True)
    partner_phone = fields.Char('Phone')
    html_3ds = fields.Char('3D Secure HTML')

    callback_eval = fields.Char('S2S Callback', help="""\
        Will be safe_eval with `self` being the current transaction. i.e.:
            self.env['my.model'].payment_validated(self)""", oldname="s2s_cb_eval", groups="base.group_system")
    payment_token_id = fields.Many2one('payment.token', 'Payment Token', domain="[('acquirer_id', '=', acquirer_id)]")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        onchange_vals = self.on_change_partner_id(self.partner_id.id).get('value', {})
        self.write(onchange_vals)

    @api.multi
    def on_change_partner_id(self, partner_id):
        partner = None
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            return {'value': {
                'partner_name': partner and partner.name or False,
                'partner_lang': partner and partner.lang or 'en_US',
                'partner_email': partner and partner.email or False,
                'partner_zip': partner and partner.zip or False,
                'partner_address': _partner_format_address(partner and partner.street or '', partner and partner.street2 or ''),
                'partner_city': partner and partner.city or False,
                'partner_country_id': partner and partner.country_id.id or self._get_default_partner_country_id(),
                'partner_phone': partner and partner.phone or False,
            }}
        return {}

    @api.constrains('reference', 'state')
    def _check_reference(self):
        for transaction in self.filtered(lambda tx: tx.state not in ('cancel', 'error')):
            if self.search_count([('reference', '=', transaction.reference)]) != 1:
                raise exceptions.ValidationError(_('The payment transaction reference must be unique!'))
        return True

    @api.model
    def create(self, values):
        if values.get('partner_id'):  # @TDENOTE: not sure
            values.update(self.on_change_partner_id(values['partner_id'])['value'])

        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

            # compute fees
            custom_method_name = '%s_compute_fees' % acquirer.provider
            if hasattr(acquirer, custom_method_name):
                fees = getattr(acquirer, custom_method_name)(
                    values.get('amount', 0.0), values.get('currency_id'), values.get('partner_country_id'))
                values['fees'] = float_round(fees, 2)

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(acquirer, custom_method_name):
                values.update(getattr(self, custom_method_name)(values))

        # Default value of reference is
        tx = super(PaymentTransaction, self).create(values)
        if not values.get('reference'):
            tx.write({'reference': str(tx.id)})
        return tx

    @api.multi
    def write(self, values):
        if ('acquirer_id' in values or 'amount' in values) and 'fees' not in values:
            # The acquirer or the amount has changed, and the fees are not explicitly forced. Fees must be recomputed.
            acquirer = None
            if values.get('acquirer_id'):
                acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
            for tx in self:
                vals = dict(values, fees=0.0)
                if not acquirer:
                    acquirer = tx.acquirer_id
                custom_method_name = '%s_compute_fees' % acquirer.provider
                # TDE FIXME: shouldn't we use fee_implemented ?
                if hasattr(acquirer, custom_method_name):
                    fees = getattr(acquirer, custom_method_name)(
                        (values['amount'] if 'amount' in values else tx.amount) or 0.0,
                        values.get('currency_id') or tx.currency_id.id,
                        values.get('partner_country_id') or tx.partner_country_id.id)
                    vals['fees'] = float_round(fees, 2)
                res = super(PaymentTransaction, tx).write(vals)
            return res
        return super(PaymentTransaction, self).write(values)

    @api.model
    def get_next_reference(self, reference):
        ref_suffix = 1
        init_ref = reference
        while self.env['payment.transaction'].sudo().search_count([('reference', '=', reference)]):
            reference = init_ref + '-' + str(ref_suffix)
            ref_suffix += 1
        return reference

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.multi
    def render(self):
        values = {
            'reference': self.reference,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'currency': self.currency_id,
            'partner': self.partner_id,
            'partner_name': self.partner_name,
            'partner_lang': self.partner_lang,
            'partner_email': self.partner_email,
            'partner_zip': self.partner_zip,
            'partner_address': self.partner_address,
            'partner_city': self.partner_city,
            'partner_country_id': self.partner_country_id.id,
            'partner_country': self.partner_country_id,
            'partner_phone': self.partner_phone,
            'partner_state': None,
        }
        return self.acquirer_id.render(None, None, None, values=values)

    @api.model
    def form_feedback(self, data, acquirer_name):
        invalid_parameters, tx = None, None

        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            tx = getattr(self, tx_find_method_name)(data)

        # TDE TODO: form_get_invalid_parameters from model to multi
        invalid_param_method_name = '_%s_form_get_invalid_parameters' % acquirer_name
        if hasattr(self, invalid_param_method_name):
            invalid_parameters = getattr(tx, invalid_param_method_name)(data)

        if invalid_parameters:
            _error_message = '%s: incorrect tx data:\n' % (acquirer_name)
            for item in invalid_parameters:
                _error_message += '\t%s: received %s instead of %s\n' % (item[0], item[1], item[2])
            _logger.error(_error_message)
            return False

        # TDE TODO: form_validate from model to multi
        feedback_method_name = '_%s_form_validate' % acquirer_name
        if hasattr(self, feedback_method_name):
            return getattr(tx, feedback_method_name)(data)

        return True

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    @api.multi
    def s2s_do_transaction(self, **kwargs):
        custom_method_name = '%s_s2s_do_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    @api.multi
    def s2s_capture_transaction(self, **kwargs):
        custom_method_name = '%s_s2s_capture_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    @api.multi
    def s2s_void_transaction(self, **kwargs):
        custom_method_name = '%s_s2s_void_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    @api.multi
    def s2s_get_tx_status(self):
        """ Get the tx status. """
        invalid_param_method_name = '_%s_s2s_get_tx_status' % self.acquirer_id.provider
        if hasattr(self, invalid_param_method_name):
            return getattr(self, invalid_param_method_name)()
        return True

    @api.multi
    def action_capture(self):
        if any(self.mapped(lambda tx: tx.state != 'authorized')):
            raise ValidationError('Only transactions in the Authorized status can be captured.')
        for tx in self:
            tx.s2s_capture_transaction()

    @api.multi
    def action_void(self):
        if any(self.mapped(lambda tx: tx.state != 'authorized')):
            raise ValidationError('Only transactions in the Authorized status can be voided.')
        for tx in self:
            tx.s2s_void_transaction()


class PaymentToken(models.Model):
    _name = 'payment.token'
    _order = 'partner_id'

    name = fields.Char('Name', help='Name of the payment token')
    short_name = fields.Char('Short name', compute='_compute_short_name')
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer Account', required=True)
    acquirer_ref = fields.Char('Acquirer Ref.', required=True)
    active = fields.Boolean('Active', default=True)
    payment_ids = fields.One2many('payment.transaction', 'payment_token_id', 'Payment Transactions')

    @api.model
    def create(self, values):
        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(values))
                # remove all non-model fields used by (provider)_create method to avoid warning
                fields_wl = set(self._fields.keys()) & set(values.keys())
                values = {field: values[field] for field in fields_wl}
        return super(PaymentToken, self).create(values)

    @api.multi
    @api.depends('name')
    def _compute_short_name(self):
        for token in self:
            token.short_name = token.name.replace('XXXXXXXXXXXX', '***')
