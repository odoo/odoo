# coding: utf-8
import hashlib
import hmac
import logging
import datetime
import pprint

from odoo import api, exceptions, fields, models, _
from odoo.tools import consteq, float_round, image_resize_images, image_resize_image, ustr
from odoo.addons.base.models import ir_module
from odoo.exceptions import ValidationError, UserError
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _partner_format_address(address1=False, address2=False):
    return ' '.join((address1 or '', address2 or '')).strip()


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


def create_missing_journal_for_acquirers(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.acquirer']._create_missing_journal_for_acquirers()


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
    _order = 'website_published desc, sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    description = fields.Html('Description')
    sequence = fields.Integer('Sequence', default=10, help="Determine the display order")
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
    # Formerly associated to `authorize` option from auto_confirm
    capture_manually = fields.Boolean(string="Capture Amount Manually",
        help="Capture the amount from Odoo, when the delivery is completed.")
    # Formerly associated to `generate_and_pay_invoice` option from auto_confirm
    journal_id = fields.Many2one(
        'account.journal', 'Payment Journal', domain=[('type', '=', 'bank')],
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1),
        help="""Payments will be registered into this journal. If you get paid straight on your bank account,
                select your bank account. If you get paid in batch for several transactions, create a specific
                payment journal for this payment acquirer to easily manage the bank reconciliation. You hold
                the amount in a temporary transfer account of your books (created automatically when you create
                the payment journal). Then when you get paid on your bank account by the payment acquirer, you
                reconcile the bank statement line with this temporary transfer account. Use reconciliation
                templates to do it in one-click.""")
    specific_countries = fields.Boolean(string="Specific Countries",
        help="If you leave it empty, the payment acquirer will be available for all the countries.")
    country_ids = fields.Many2many(
        'res.country', 'payment_country_rel',
        'payment_id', 'country_id', 'Countries',
        help="This payment gateway is available for selected countries. If none is selected it is available for all countries.")

    pre_msg = fields.Html(
        'Help Message', translate=True,
        help='Message displayed to explain and help the payment process.')
    post_msg = fields.Html(
        'Thanks Message', translate=True,
        help='Message displayed after having done the payment process.')
    pending_msg = fields.Html(
        'Pending Message', translate=True,
        default=lambda s: _('<i>Pending,</i> Your online payment has been successfully processed. But your order is not validated yet.'),
        help='Message displayed, if order is in pending state after having done the payment process.')
    done_msg = fields.Html(
        'Done Message', translate=True,
        default=lambda s: _('<i>Done,</i> Your online payment has been successfully processed. Thank you for your order.'),
        help='Message displayed, if order is done successfully after having done the payment process.')
    cancel_msg = fields.Html(
        'Cancel Message', translate=True,
        default=lambda s: _('<i>Cancel,</i> Your payment has been cancelled.'),
        help='Message displayed, if order is cancel during the payment process.')
    error_msg = fields.Html(
        'Error Message', translate=True,
        default=lambda s: _('<i>Error,</i> Please be aware that an error occurred during the transaction. The order has been confirmed but will not be paid. Do not hesitate to contact us if you have any questions on the status of your order.'),
        help='Message displayed, if error is occur during the payment process.')
    save_token = fields.Selection([
        ('none', 'Never'),
        ('ask', 'Let the customer decide'),
        ('always', 'Always')],
        string='Save Cards', default='none',
        help="This option allows customers to save their credit card as a payment token and to reuse it for a later purchase. "
             "If you manage subscriptions (recurring invoicing), you need it to automatically charge the customer when you "
             "issue an invoice.")
    token_implemented = fields.Boolean('Saving Card Data supported', compute='_compute_feature_support', search='_search_is_tokenized')
    authorize_implemented = fields.Boolean('Authorize Mechanism Supported', compute='_compute_feature_support')
    fees_implemented = fields.Boolean('Fees Computation Supported', compute='_compute_feature_support')
    fees_active = fields.Boolean('Add Extra Fees')
    fees_dom_fixed = fields.Float('Fixed domestic fees')
    fees_dom_var = fields.Float('Variable domestic fees (in percents)')
    fees_int_fixed = fields.Float('Fixed international fees')
    fees_int_var = fields.Float('Variable international fees (in percents)')

    # TDE FIXME: remove that brol
    module_id = fields.Many2one('ir.module.module', string='Corresponding Module')
    module_state = fields.Selection(selection=ir_module.STATES, string='Installation State', related='module_id.state')

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

    payment_icon_ids = fields.Many2many('payment.icon', string='Supported Payment Icons')
    payment_flow = fields.Selection(selection=[('form', 'Redirection to the acquirer website'),
        ('s2s','Payment from Odoo')],
        default='form', required=True, string='Payment Flow',
        help="""Note: Subscriptions does not take this field in account, it uses server to server by default.""")

    def _search_is_tokenized(self, operator, value):
        tokenized = self._get_feature_support()['tokenize']
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('provider', 'in', tokenized)]
        return [('provider', 'not in', tokenized)]

    @api.multi
    def _compute_feature_support(self):
        feature_support = self._get_feature_support()
        for acquirer in self:
            acquirer.fees_implemented = acquirer.provider in feature_support['fees']
            acquirer.authorize_implemented = acquirer.provider in feature_support['authorize']
            acquirer.token_implemented = acquirer.provider in feature_support['tokenize']

    @api.multi
    def _check_required_if_provider(self):
        """ If the field has 'required_if_provider="<provider>"' attribute, then it
        required if record.provider is <provider>. """
        for acquirer in self:
            if any(getattr(f, 'required_if_provider', None) == acquirer.provider and not acquirer[k] for k, f in self._fields.items()):
                return False
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

    @api.multi
    def _prepare_account_journal_vals(self):
        '''Prepare the values to create the acquirer's journal.

        :return: a dictionary to create a account.journal record.
        '''
        self.ensure_one()
        account_vals = self.env['account.journal']._prepare_liquidity_account(
            self.name, self.company_id, None, 'transfer')
        account_vals['user_type_id'] = self.env.ref('account.data_account_type_current_assets').id
        account_vals['reconcile'] = True
        account = self.env['account.account'].create(account_vals)
        return {
            'name': self.name,
            'code': self.name.upper(),
            'type': 'bank',
            'company_id': self.company_id.id,
            'default_debit_account_id': account.id,
            'default_credit_account_id': account.id,
            # Show the journal on dashboard if the acquirer is published on the website.
            'show_on_dashboard': self.website_published,
            # Don't show payment methods in the backend.
            'inbound_payment_method_ids': [],
            'outbound_payment_method_ids': [],
        }

    @api.model
    def _create_missing_journal_for_acquirers(self):
        '''Create the journal for active acquirers.

        We want one journal per acquirer. However, we can't create them during the 'create' of the payment.acquirer
        because every acquirers are defined on the 'payment' module but is active only when installing their own module
        (e.g. payment_paypal for Paypal). We can't do that in such modules because we have no guarantee the chart template
        is already installed.
        '''
        # Search for installed acquirers modules.
        # If this method is triggered by a post_init_hook, the module is 'to install'.
        # If the trigger comes from the chart template wizard, the modules are already installed.
        acquirer_modules = self.env['ir.module.module'].search(
            [('name', 'like', 'payment_%'), ('state', 'in', ('to install', 'installed'))])
        acquirer_names = [a.name.split('_')[1] for a in acquirer_modules]

        # Search for acquirers having no journal
        company = self.env.user.company_id
        acquirers = self.env['payment.acquirer'].search(
            [('provider', 'in', acquirer_names), ('journal_id', '=', False), ('company_id', '=', company.id)])

        journals = self.env['account.journal']
        for acquirer in acquirers.filtered(lambda l: not l.journal_id and l.company_id.chart_template_id):
            acquirer.journal_id = self.env['account.journal'].create(acquirer._prepare_account_journal_vals())
            journals += acquirer.journal_id
        return journals

    @api.model
    def create(self, vals):
        image_resize_images(vals)
        return super(PaymentAcquirer, self).create(vals)

    @api.multi
    def write(self, vals):
        image_resize_images(vals)
        return super(PaymentAcquirer, self).write(vals)

    @api.multi
    def toggle_website_published(self):
        self.website_published = not self.website_published
        if self.journal_id:
            self.journal_id.show_on_dashboard = self.website_published
        return True

    @api.multi
    def get_form_action_url(self):
        """ Returns the form action URL, for form-based acquirer implementations. """
        if hasattr(self, '%s_get_form_action_url' % self.provider):
            return getattr(self, '%s_get_form_action_url' % self.provider)()
        return False

    def _get_available_payment_input(self, partner=None, company=None):
        """ Generic (model) method that fetches available payment mechanisms
        to use in all portal / eshop pages that want to use the payment form.

        It contains

         * form_acquirers: record set of acquirers based on a local form that
                           sends customer to the acquirer website;
         * s2s_acquirers: reset set of acquirers that send customer data to
                          acquirer without redirecting to any other website;
         * pms: record set of stored credit card data (aka payment.token)
                connected to a given partner to allow customers to reuse them """
        if not company:
            company = self.env.user.company_id
        if not partner:
            partner = self.env.user.partner_id
        active_acquirers = self.sudo().search([('website_published', '=', True), ('company_id', '=', company.id)])
        form_acquirers = active_acquirers.filtered(lambda acq: acq.payment_flow == 'form' and acq.view_template_id)
        s2s_acquirers = active_acquirers.filtered(lambda acq: acq.payment_flow == 's2s' and acq.registration_view_template_id)
        return {
            'form_acquirers': form_acquirers,
            's2s_acquirers': s2s_acquirers,
            'pms': self.env['payment.token'].search([
                ('partner_id', '=', partner.id),
                ('acquirer_id', 'in', s2s_acquirers.ids)]),
        }

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

        _logger.info('payment.acquirer.render: <%s> values rendered for form payment:\n%s', self.provider, pprint.pformat(values))
        return self.view_template_id.render(values, engine='ir.qweb')

    def get_s2s_form_xml_id(self):
        if self.registration_view_template_id:
            model_data = self.env['ir.model.data'].search([('model', '=', 'ir.ui.view'), ('res_id', '=', self.registration_view_template_id.id)])
            return ('%s.%s') % (model_data.module, model_data.name)
        return False

    @api.multi
    def s2s_process(self, data):
        cust_method_name = '%s_s2s_form_process' % (self.provider)
        if not self.s2s_validate(data):
            return False
        if hasattr(self, cust_method_name):
            # As this method may be called in JSON and overriden in various addons
            # let us raise interesting errors before having stranges crashes
            if not data.get('partner_id'):
                raise ValueError(_('Missing partner reference when trying to create a new payment token'))
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
    def toggle_environment_value(self):
        prod = self.filtered(lambda acquirer: acquirer.environment == 'prod')
        prod.write({'environment': 'test'})
        (self-prod).write({'environment': 'prod'})

    @api.multi
    def button_immediate_install(self):
        # TDE FIXME: remove that brol
        if self.module_id and self.module_state != 'installed':
            self.module_id.button_immediate_install()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

class PaymentIcon(models.Model):
    _name = 'payment.icon'
    _description = 'Payment Icon'

    name = fields.Char(string='Name')
    acquirer_ids = fields.Many2many('payment.acquirer', string="Acquirers", help="List of Acquirers supporting this payment icon.")
    image = fields.Binary(
        "Image", attachment=True,
        help="This field holds the image used for this payment icon, limited to 1024x1024px")

    image_payment_form = fields.Binary(
        "Image displayed on the payment form", attachment=True)

    @api.model
    def create(self, vals):
        if 'image' in vals:
            image = ustr(vals['image'] or '').encode('utf-8')
            vals['image_payment_form'] = image_resize_image(image, size=(45,30))
            vals['image'] = image_resize_image(image, size=(64,64))
        return super(PaymentIcon, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'image' in vals:
            image = ustr(vals['image'] or '').encode('utf-8')
            vals['image_payment_form'] = image_resize_image(image, size=(45,30))
            vals['image'] = image_resize_image(image, size=(64,64))
        return super(PaymentIcon, self).write(vals)

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
    _inherits = {'account.payment': 'payment_id'}
    _description = 'Payment Transaction'
    _order = 'id desc'
    _rec_name = 'reference'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _get_default_partner_country_id(self):
        return self.env['res.company']._company_default_get('payment.transaction').country_id.id

    # Field making the one2one relation with the account.payment. Mirror of the payment_transaction_id field.
    payment_id = fields.Many2one('account.payment', string='Payment',
                                 required=True, readonly=True, ondelete='cascade')

    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer', required=True)
    provider = fields.Selection(string='Provider', related='acquirer_id.provider')
    type = fields.Selection([
        ('validation', 'Validation of the bank card'),
        ('server2server', 'Server To Server'),
        ('form', 'Form'),
        ('form_save', 'Form with tokenization')], 'Type',
        default='form', required=True)
    pending = fields.Boolean(string='Pending', readonly=True,
                             help='The transaction has already been updated by the remote server.')
    capture = fields.Boolean(string='Capture', readonly=True,
                                help='The amount of the transaction can be captured manually.')
    state_message = fields.Text('Message', help='Field used to store error and/or validation messages for information')
    # payment
    fees = fields.Monetary(
        'Fees', currency_field='currency_id', track_visibility='always',
        help='Fees amount; set by the system because depends on the acquirer')
    reference = fields.Char('Reference', required=True, default='Draft Transaction', readonly=True,
                            help='Internal reference of the transaction.')
    acquirer_reference = fields.Char('Acquirer Reference', help='Reference of the TX as stored in the acquirer database')
    # duplicate partner / transaction data to store the values at transaction time
    partner_name = fields.Char('Partner Name')
    partner_lang = fields.Selection(_lang_get, 'Language', default=lambda self: self.env.lang)
    partner_email = fields.Char('Email')
    partner_zip = fields.Char('Zip')
    partner_address = fields.Char('Address')
    partner_city = fields.Char('City')
    partner_country_id = fields.Many2one('res.country', 'Country', default=_get_default_partner_country_id, required=True)
    partner_phone = fields.Char('Phone')
    html_3ds = fields.Char('3D Secure HTML')

    callback_model_id = fields.Many2one('ir.model', 'Callback Document Model', groups="base.group_system")
    callback_res_id = fields.Integer('Callback Document ID', groups="base.group_system")
    callback_method = fields.Char('Callback Method', groups="base.group_system")
    callback_hash = fields.Char('Callback Hash', groups="base.group_system")

    payment_token_id = fields.Many2one('payment.token', 'Payment Token', domain="[('acquirer_id', '=', acquirer_id)]")

    token_implemented = fields.Boolean(related='acquirer_id.token_implemented')
    authorize_implemented = fields.Boolean(related='acquirer_id.authorize_implemented')
    fees_implemented = fields.Boolean(related='acquirer_id.fees_implemented')

    _sql_constraints = [
        ('reference_uniq', 'unique(reference)', 'Reference must be unique!'),
    ]

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        onchange_vals = self.on_change_partner_id(self.partner_id.id).get('value', {})
        self.update(onchange_vals)

    @api.onchange('payment_method_id', 'journal_id')
    def _onchange_payment_method(self):
        if self.payment_method_code == 'electronic':
            self.payment_token_id = self.env['payment.token'].search(
                [('partner_id', '=', self.partner_id.id), ('acquirer_id.capture_manually', '=', False)], limit=1)
        else:
            self.payment_token_id = False

    @api.multi
    def _get_oe_log_html(self):
        self.ensure_one()
        return '<a href=# data-oe-model=payment.transaction data-oe-id=%d>%s</a>' % (self.id, self.reference)

    @api.multi
    def _log_payment_transaction_sent(self):
        '''Log the message saying the transaction has been sent to the remote server to be
        processed by the acquirer.
        '''
        message = 'Transaction %s sent to the acquirer %s:'
        for trans in self:
            values = []
            if trans.payment_token_id:
                values.append('%s: %s' % (_('Token'), trans.payment_token_id._get_oe_log_html()))
            values.append('%s: %s' % (_('Date'), fields.datetime.now()))
            post_message = message % (trans._get_oe_log_html(), trans.acquirer_id.name)
            post_message += '<ul><li>' + '</li><li>'.join(values) + '</li></ul>'
            trans.payment_id.message_post(body=post_message)

    @api.multi
    def _log_payment_transaction_received(self):
        '''Log the message saying a response has been received from the remote server and some
        additional informations like the old/new state, the reference of the payment... etc.

        :param old_state:       The state of the transaction before the response.
        :param add_messages:    Optional additional messages to log like the capture status.
        '''
        message = _('Transaction %s updated by the acquirer %s:')

        for trans in self:
            values = ['%s: %s' % (_('Date'), fields.datetime.now())]

            if trans.state_message:
                values = ['%s: %s' % (_('Response'), trans.state_message)] + values

            if trans.acquirer_reference:
                values = ['%s: %s' % (_('Reference'), trans.acquirer_reference)] + values

            if trans.state == 'draft' and trans.capture:
                values = ['%s: %s' % (_('Capture'), _('Allowed'))] + values
            elif trans.state == 'posted' and trans.capture:
                values = ['%s: %s' % (_('Capture'), _('Success'))] + values
            elif trans.state == 'cancelled' and trans.capture:
                    values = ['%s: %s' % (_('Capture'), _('Voided'))] + values

            if trans.state != 'draft':
                values = ['%s -> %s' % (_('Draft'), trans.state)] + values

            post_message = message % (trans._get_oe_log_html(), trans.acquirer_id.name)
            post_message += '<ul><li>' + '</li><li>'.join(values) + '</li></ul>'
            trans.payment_id.message_post(body=post_message)

    @api.multi
    def _set_transaction_pending(self):
        '''Move the transaction to the pending state(e.g. Wire Transfer).
        Then, the account.payment must be processed manually by the user.
        Only transaction that are not already processed can be set to the pending state.
        '''
        if any(trans.state != 'draft' or trans.pending or trans.capture for trans in self):
            raise UserError(_('Some transactions can\'t be processed because they are already pending, capture or not linked to draft payment.'))
        self.write({'pending': True})
        self._log_payment_transaction_received()

    @api.multi
    def _set_transaction_capture(self):
        '''Move the transaction to the capture state(e.g. Authorize).
        Then, the account.payment amount must be captured manually by the user using the 'Capture' button on the form view.
        Only transaction that are not already processed can be set to the capture state.
        '''
        if any(trans.state != 'draft' or trans.pending or trans.capture for trans in self):
            raise UserError(_('Some transactions can\'t be processed because they are already pending, capture or not linked to draft payment.'))
        self.write({'pending': True, 'capture': True})
        self._log_payment_transaction_received()

    @api.multi
    def _set_transaction_posted(self):
        '''Move the transaction's payment to the posted state(e.g. Paypal).
        Only draft transactions can be posted (including the transactions to capture).
        '''
        if any(trans.state != 'draft' for trans in self):
            raise UserError(_('Some transactions can\'t be processed because they are not linked to draft payment.'))

        # Validate invoices automatically upon the transaction is posted.
        invoices = self.mapped('invoice_ids').filtered(lambda inv: inv.state == 'draft')
        invoices.action_invoice_open()

        self.payment_id.post()

        self.write({'pending': True, 'capture': False})
        self._log_payment_transaction_received()

    @api.multi
    def _set_transaction_cancel(self):
        '''Move the transaction's payment to the cancelled state(e.g. Paypal).
        Only draft transactions can be cancelled (including the transactions to capture).
        '''
        if any(trans.state != 'draft' for trans in self):
            raise UserError(_('Some transactions can\'t be cancelled because they are not linked to draft payment.'))

        self.payment_id.cancel()

        self.write({'pending': True, 'capture': False})
        self._log_payment_transaction_received()

    @api.multi
    def on_change_partner_id(self, partner_id):
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

    @api.constrains('capture', 'state', 'acquirer_id')
    def _check_authorize_state(self):
        failed_tx = self.filtered(lambda tx: tx.capture and tx.acquirer_id.provider not in self.env['payment.acquirer']._get_feature_support()['authorize'])
        if failed_tx:
            raise exceptions.ValidationError(_('The %s payment acquirers are not allowed to manual capture mode!' % failed_tx.mapped('acquirer_id.name')))

    @api.model
    def _prepare_account_payment_vals(self, vals, acquirer=None):
        '''Prepare values to create the account.payment record.
        :param vals: vals used during the create.
        :param acquirer: The payment.acquirer record to browsing twice.
        :return: a dictionary of values.
        '''
        if not acquirer:
            acquirer = self.env['payment.acquirer'].browse(vals['acquirer_id'])

        if not acquirer.journal_id:
            raise UserError(_('A journal must be specified of the acquirer %s.' % acquirer.name))

        amount = vals.get('amount')
        payment_type = 'inbound' if amount > 0 else 'outbound'
        invoice_ids = vals.get('invoice_ids')
        return {
            'amount': amount,
            'partner_id': vals.get('partner_id'),
            'partner_type': 'customer',
            'invoice_ids': invoice_ids,
            'currency_id': vals.get('currency_id'),
            'journal_id': acquirer.journal_id.id,
            'company_id': acquirer.company_id.id,
            'payment_method_id': self.env.ref('payment.account_payment_method_electronic_in').id,
            'payment_type': payment_type,
            'state': 'draft',
        }

    @api.model
    def _compute_reference(self, vals=None):
        '''Compute a unique reference for the transaction.
        If some invoices:
            <inv_number_0>.number,<inv_number_1>,...,<inv_number_n>-x
        If some sale orders:
            <so_name_0>.number,<so_name_1>,...,<so_name_n>-x
        :param vals: values passed on the create function.
        :return: A unique reference for the transaction.
        '''
        def as_reference(many_field, ref_field):
            many_list = self.resolve_2many_commands(many_field, vals[many_field], fields=[ref_field])
            return ','.join(dic[ref_field] for dic in many_list)

        reference = ''
        if vals and vals.get('invoice_ids'):
            reference = as_reference('invoice_ids', 'number')
        elif vals and vals.get('sale_order_ids'):
            reference = as_reference('sale_order_ids', 'name')

        # Fetch the last reference
        # E.g. If the last reference is SO42-5, this query will return '-5'
        self._cr.execute('''
            SELECT CAST(SUBSTRING(reference FROM '-\d+') AS INTEGER) AS suffix
            FROM payment_transaction WHERE reference LIKE %s ORDER BY suffix
        ''', [reference + '%'])
        query_res = self._cr.fetchone()

        if query_res:
            # Increment the last reference by one
            reference += '-%s' % (-query_res[0] + 1)
        else:
            # Start a new indexing from 1
            reference += '-1'
        return reference

    @api.model
    def create(self, values):
        if values.get('partner_id'):  # @TDENOTE: not sure
            values.update(self.on_change_partner_id(values['partner_id'])['value'])

        # call custom create method if defined (i.e. ogone_create for ogone)
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

        payment_record = None
        if values.get('payment_id'):
            payment_record = self.env['account.payment'].browse(values['payment_id'])
        else:
            payment_record = self.env['account.payment'].sudo().create(
                self._prepare_account_payment_vals(values, acquirer=acquirer))
            values['payment_id'] = payment_record.id

        if not values.get('reference'):
            values['reference'] = self._compute_reference(values)

        # The invoice_ids fields is declared on account.payment.
        # Then, no need to write this value again.
        if 'invoice_ids' in values:
            values.pop('invoice_ids')

        # Default value of reference is
        tx = super(PaymentTransaction, self).create(values)

        # Assign the id to the account.payment to make a one2one relation.
        payment_record.payment_transaction_id = tx.id

        # Generate callback hash if it is configured on the tx; avoid generating unnecessary stuff
        # (limited sudo env for checking callback presence, must work for manual transactions too)
        tx_sudo = tx.sudo()
        if tx_sudo.callback_model_id and tx_sudo.callback_res_id and tx_sudo.callback_method:
            tx.write({'callback_hash': tx._generate_callback_hash()})

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

    def _generate_callback_hash(self):
        self.ensure_one()
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token = '%s%s%s' % (self.callback_model_id.model,
                            self.callback_res_id,
                            self.sudo().callback_method)
        return hmac.new(secret.encode('utf-8'), token.encode('utf-8'), hashlib.sha256).hexdigest()

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

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
        self._log_payment_transaction_sent()
        custom_method_name = '%s_s2s_do_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    @api.multi
    def s2s_do_refund(self, **kwargs):
        custom_method_name = '%s_s2s_do_refund' % self.acquirer_id.provider
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
    def execute_callback(self):
        res = None
        for transaction in self:
            # limited sudo env, only for checking callback presence, not for running it!
            # manual transactions have no callback, and can pass without being run by admin user
            tx_sudo = transaction.sudo()
            if not (tx_sudo.callback_model_id and tx_sudo.callback_res_id and tx_sudo.callback_method):
                continue

            valid_token = transaction._generate_callback_hash()
            if not consteq(ustr(valid_token), transaction.callback_hash):
                _logger.warning("Invalid callback signature for transaction %d" % (transaction.id))
                continue

            record = self.env[transaction.callback_model_id.model].browse(transaction.callback_res_id).exists()
            if record:
                res = getattr(record, transaction.callback_method)(transaction)
            else:
                _logger.warning("Did not found record %s.%s for callback of transaction %d" % (transaction.callback_model_id.model, transaction.callback_res_id, transaction.id))
        return res

    @api.multi
    def action_capture(self):
        if any([not t.capture for t in self]):
            raise ValidationError(_('Only transactions having the capture status can be captured.'))
        for tx in self:
            tx.s2s_capture_transaction()

    @api.multi
    def action_void(self):
        if any([not t.capture for t in self]):
            raise ValidationError(_('Only transactions having the capture status can be voided.'))
        for tx in self:
            tx.s2s_void_transaction()


class PaymentToken(models.Model):
    _name = 'payment.token'
    _order = 'partner_id, id desc'

    name = fields.Char('Name', help='Name of the payment token')
    short_name = fields.Char('Short name', compute='_compute_short_name')
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer Account', required=True)
    acquirer_ref = fields.Char('Acquirer Ref.', required=True)
    active = fields.Boolean('Active', default=True)
    payment_ids = fields.One2many('payment.transaction', 'payment_token_id', 'Payment Transactions')
    verified = fields.Boolean(string='Verified', default=False)

    @api.multi
    def _get_oe_log_html(self):
        self.ensure_one()
        return '<a href=# data-oe-model=payment.token data-oe-id=%d>%s</a>' % (self.id, self.name)

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
                fields_wl = set(self._fields) & set(values)
                values = {field: values[field] for field in fields_wl}
        return super(PaymentToken, self).create(values)
    """
        @TBE: stolen shamelessly from there https://www.paypal.com/us/selfhelp/article/why-is-there-a-$1.95-charge-on-my-card-statement-faq554
        Most of them are ~1.50€s
        TODO: See this with @AL & @DBO
    """
    VALIDATION_AMOUNTS = {
        'CAD': 2.45,
        'EUR': 1.50,
        'GBP': 1.00,
        'JPY': 200,
        'AUD': 2.00,
        'NZD': 3.00,
        'CHF': 3.00,
        'HKD': 15.00,
        'SEK': 15.00,
        'DKK': 12.50,
        'PLN': 6.50,
        'NOK': 15.00,
        'HUF': 400.00,
        'CZK': 50.00,
        'BRL': 4.00,
        'MYR': 10.00,
        'MXN': 20.00,
        'ILS': 8.00,
        'PHP': 100.00,
        'TWD': 70.00,
        'THB': 70.00
        }

    @api.model
    def validate(self, **kwargs):
        """
            This method allow to verify if this payment method is valid or not.
            It does this by withdrawing a certain amount and then refund it right after.
        """
        currency = self.partner_id.currency_id

        if self.VALIDATION_AMOUNTS.get(currency.name):
            amount = self.VALIDATION_AMOUNTS.get(currency.name)
        else:
            # If we don't find the user's currency, then we set the currency to EUR and the amount to 1€50.
            currency = self.env['res.currency'].search([('name', '=', 'EUR')])
            amount = 1.5

        if len(currency) != 1:
            _logger.error("Error 'EUR' currency not found for payment method validation!")
            return False

        reference = "VALIDATION-%s-%s" % (self.id, datetime.datetime.now().strftime('%y%m%d_%H%M%S'))
        tx = self.env['payment.transaction'].sudo().create({
            'amount': amount,
            'acquirer_id': self.acquirer_id.id,
            'type': 'validation',
            'currency_id': currency.id,
            'reference': reference,
            'payment_token_id': self.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
        })

        try:
            kwargs.update({'3d_secure': True})
            tx.s2s_do_transaction(**kwargs)
            # if 3D secure is called, then we do not refund right now
            if tx.html_3ds:
                return tx
        except:
            _logger.error('Error while validating a payment method')
        finally:
            tx.s2s_do_refund()
        return tx

    @api.multi
    @api.depends('name')
    def _compute_short_name(self):
        for token in self:
            token.short_name = token.name.replace('XXXXXXXXXXXX', '***')

    @api.multi
    def get_linked_records(self):
        """ This method returns a dict containing all the records linked to the payment.token (e.g Subscriptions),
            the key is the id of the payment.token and the value is an array that must follow the scheme below.

            {
                token_id: [
                    'description': The model description (e.g 'Sale Subscription'),
                    'id': The id of the record,
                    'name': The name of the record,
                    'url': The url to access to this record.
                ]
            }
        """
        return {r.id:[] for r in self}
