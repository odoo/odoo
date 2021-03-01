# coding: utf-8
from collections import defaultdict
import hashlib
import hmac
import logging
from datetime import datetime
from dateutil import relativedelta
import pprint
import psycopg2

from odoo import api, exceptions, fields, models, _, SUPERUSER_ID
from odoo.tools import consteq, float_round, image_process, ustr
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.http import request
from odoo.osv import expression

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
    a button used to display the payment form. See examples in ``payment_ingenico``
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
    _order = 'module_state, state, sequence, name'

    def _valid_field_parameter(self, field, name):
        return name == 'required_if_provider' or super()._valid_field_parameter(field, name)

    def _get_default_view_template_id(self):
        return self.env.ref('payment.default_acquirer_button', raise_if_not_found=False)

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color', compute='_compute_color', store=True)
    display_as = fields.Char('Displayed as', translate=True, help="How the acquirer is displayed to the customers.")
    description = fields.Html('Description')
    sequence = fields.Integer('Sequence', default=10, help="Determine the display order")
    provider = fields.Selection(
        selection=[('manual', 'Custom Payment Form')], string='Provider',
        default='manual', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company.id, required=True)
    view_template_id = fields.Many2one(
        'ir.ui.view', 'Form Button Template',
        default=_get_default_view_template_id,
        help="This template renders the acquirer button with all necessary values.\n"
        "It is rendered with qWeb with the following evaluation context:\n"
        "tx_url: transaction URL to post the form\n"
        "acquirer: payment.acquirer browse record\n"
        "user: current user browse record\n"
        "reference: the transaction reference number\n"
        "currency: the transaction currency browse record\n"
        "amount: the transaction amount, a float\n"
        "partner: the buyer partner browse record, not necessarily set\n"
        "partner_values: specific values about the buyer, for example coming from a shipping form\n"
        "tx_values: transaction values\n"
        "context: the current context dictionary")
    registration_view_template_id = fields.Many2one(
        'ir.ui.view', 'S2S Form Template', domain=[('type', '=', 'qweb')],
        help="Template for method registration")
    state = fields.Selection([
        ('disabled', 'Disabled'),
        ('enabled', 'Enabled'),
        ('test', 'Test Mode')], required=True, default='disabled', copy=False,
        help="""In test mode, a fake payment is processed through a test
             payment interface. This mode is advised when setting up the
             acquirer. Watch out, test and production modes require
             different credentials.""")
    capture_manually = fields.Boolean(string="Capture Amount Manually",
        help="Capture the amount from Odoo, when the delivery is completed.")
    journal_id = fields.Many2one(
        'account.journal', 'Payment Journal', domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]",
        help="""Journal where the successful transactions will be posted""")
    check_validity = fields.Boolean(string="Verify Card Validity",
        help="""Trigger a transaction of 1 currency unit and its refund to check the validity of new credit cards entered in the customer portal.
        Without this check, the validity will be verified at the very first transaction.""")
    country_ids = fields.Many2many(
        'res.country', 'payment_country_rel',
        'payment_id', 'country_id', 'Countries',
        help="This payment gateway is available for selected countries. If none is selected it is available for all countries.")

    pre_msg = fields.Html(
        'Help Message', translate=True,
        help='Message displayed to explain and help the payment process.')
    auth_msg = fields.Html(
        'Authorize Message', translate=True,
        default=lambda s: _('Your payment has been authorized.'),
        help='Message displayed if payment is authorized.')
    pending_msg = fields.Html(
        'Pending Message', translate=True,
        default=lambda s: _('Your payment has been successfully processed but is waiting for approval.'),
        help='Message displayed, if order is in pending state after having done the payment process.')
    done_msg = fields.Html(
        'Done Message', translate=True,
        default=lambda s: _('Your payment has been successfully processed. Thank you!'),
        help='Message displayed, if order is done successfully after having done the payment process.')
    cancel_msg = fields.Html(
        'Cancel Message', translate=True,
        default=lambda s: _('Your payment has been cancelled.'),
        help='Message displayed, if order is cancel during the payment process.')
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
    qr_code = fields.Boolean('Enable QR Codes', help="Enable the use of QR-codes for payments made on this provider.")

    # TDE FIXME: remove that brol
    module_id = fields.Many2one('ir.module.module', string='Corresponding Module')
    module_state = fields.Selection(string='Installation State', related='module_id.state', store=True)
    module_to_buy = fields.Boolean(string='Odoo Enterprise Module', related='module_id.to_buy', readonly=True, store=False)

    image_128 = fields.Image("Image", max_width=128, max_height=128)

    payment_icon_ids = fields.Many2many('payment.icon', string='Supported Payment Icons')
    payment_flow = fields.Selection(selection=[('form', 'Redirection to the acquirer website'),
        ('s2s','Payment from Odoo')],
        default='form', required=True, string='Payment Flow',
        help="""Note: Subscriptions does not take this field in account, it uses server to server by default.""")
    inbound_payment_method_ids = fields.Many2many('account.payment.method', related='journal_id.inbound_payment_method_ids', readonly=False)

    @api.onchange('payment_flow')
    def _onchange_payment_flow(self):
        electronic = self.env.ref('payment.account_payment_method_electronic_in')
        if self.token_implemented and self.payment_flow == 's2s':
            if electronic not in self.inbound_payment_method_ids:
                self.inbound_payment_method_ids = [(4, electronic.id)]
        elif electronic in self.inbound_payment_method_ids:
            self.inbound_payment_method_ids = [(2, electronic.id)]

    @api.onchange('state')
    def onchange_state(self):
        """Disable dashboard display for test acquirer journal."""
        self.journal_id.update({'show_on_dashboard': self.state == 'enabled'})

    def _search_is_tokenized(self, operator, value):
        tokenized = self._get_feature_support()['tokenize']
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('provider', 'in', tokenized)]
        return [('provider', 'not in', tokenized)]

    @api.depends('provider')
    def _compute_feature_support(self):
        feature_support = self._get_feature_support()
        for acquirer in self:
            acquirer.fees_implemented = acquirer.provider in feature_support['fees']
            acquirer.authorize_implemented = acquirer.provider in feature_support['authorize']
            acquirer.token_implemented = acquirer.provider in feature_support['tokenize']

    @api.depends('state', 'module_state')
    def _compute_color(self):
        for acquirer in self:
            if acquirer.module_id and not acquirer.module_state == 'installed':
                acquirer.color = 4  # blue
            elif acquirer.state == 'disabled':
                acquirer.color = 3  # yellow
            elif acquirer.state == 'test':
                acquirer.color = 2  # orange
            elif acquirer.state == 'enabled':
                acquirer.color = 7  # green

    def _check_required_if_provider(self):
        """ If the field has 'required_if_provider="<provider>"' attribute, then it
        required if record.provider is <provider>. """
        field_names = []
        enabled_acquirers = self.filtered(lambda acq: acq.state in ['enabled', 'test'])
        for k, f in self._fields.items():
            provider = getattr(f, 'required_if_provider', None)
            if provider and any(
                acquirer.provider == provider and not acquirer[k]
                for acquirer in enabled_acquirers
            ):
                ir_field = self.env['ir.model.fields']._get(self._name, k)
                field_names.append(ir_field.field_description)
        if field_names:
            raise ValidationError(_("Required fields not filled: %s") % ", ".join(field_names))

    def get_base_url(self):
        self.ensure_one()
        # priority is always given to url_root
        # from the request
        url = ''
        if request:
            url = request.httprequest.url_root

        if not url and 'website_id' in self and self.website_id:
            url = self.website_id._get_http_domain()

        return url or self.env['ir.config_parameter'].sudo().get_param('web.base.url')

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

    def _prepare_account_journal_vals(self):
        '''Prepare the values to create the acquirer's journal.
        :return: a dictionary to create a account.journal record.
        '''
        self.ensure_one()
        account_vals = self.company_id.chart_template_id._prepare_transfer_account_for_direct_creation(self.name, self.company_id)
        account = self.env['account.account'].create(account_vals)
        inbound_payment_method_ids = []
        if self.token_implemented and self.payment_flow == 's2s':
            inbound_payment_method_ids.append((4, self.env.ref('payment.account_payment_method_electronic_in').id))
        return {
            'name': self.name,
            'code': self.name.upper(),
            'sequence': 999,
            'type': 'bank',
            'company_id': self.company_id.id,
            'default_account_id': account.id,
            # Show the journal on dashboard if the acquirer is published on the website.
            'show_on_dashboard': self.state == 'enabled',
            # Don't show payment methods in the backend.
            'inbound_payment_method_ids': inbound_payment_method_ids,
            'outbound_payment_method_ids': [],
        }

    def _get_acquirer_journal_domain(self):
        """Returns a domain for finding a journal corresponding to an acquirer"""
        self.ensure_one()
        code_cutoff = self.env['account.journal']._fields['code'].size
        return [
            ('name', '=', self.name),
            ('code', '=', self.name.upper()[:code_cutoff]),
            ('company_id', '=', self.company_id.id),
        ]

    @api.model
    def _create_missing_journal_for_acquirers(self, company=None):
        '''Create the journal for active acquirers.
        We want one journal per acquirer. However, we can't create them during the 'create' of the payment.acquirer
        because every acquirers are defined on the 'payment' module but is active only when installing their own module
        (e.g. payment_paypal for Paypal). We can't do that in such modules because we have no guarantee the chart template
        is already installed.
        '''
        # Search for installed acquirers modules that have no journal for the current company.
        # If this method is triggered by a post_init_hook, the module is 'to install'.
        # If the trigger comes from the chart template wizard, the modules are already installed.
        company = company or self.env.company
        acquirers = self.env['payment.acquirer'].search([
            ('module_state', 'in', ('to install', 'installed')),
            ('journal_id', '=', False),
            ('company_id', '=', company.id),
        ])

        # Here we will attempt to first create the journal since the most common case (first
        # install) is to successfully to create the journal for the acquirer, in the case of a
        # reinstall (least common case), the creation will fail because of a unique constraint
        # violation, this is ok as we catch the error and then perform a search if need be
        # and assign the existing journal to our reinstalled acquirer. It is better to ask for
        # forgiveness than to ask for permission as this saves us the overhead of doing a select
        # that would be useless in most cases.
        Journal = journals = self.env['account.journal']
        for acquirer in acquirers.filtered(lambda l: not l.journal_id and l.company_id.chart_template_id):
            try:
                with self.env.cr.savepoint():
                    journal = Journal.create(acquirer._prepare_account_journal_vals())
            except psycopg2.IntegrityError as e:
                if e.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                    journal = Journal.search(acquirer._get_acquirer_journal_domain(), limit=1)
                else:
                    raise
            acquirer.journal_id = journal
            journals += journal
        return journals

    @api.model
    def create(self, vals):
        record = super(PaymentAcquirer, self).create(vals)
        record._check_required_if_provider()
        return record

    def write(self, vals):
        result = super(PaymentAcquirer, self).write(vals)
        self._check_required_if_provider()
        return result

    def get_acquirer_extra_fees(self, amount, currency_id, country_id):
        extra_fees = {
            'currency_id': currency_id
        }
        acquirers = self.filtered(lambda x: x.fees_active)
        for acq in acquirers:
            custom_method_name = '%s_compute_fees' % acq.provider
            if hasattr(acq, custom_method_name):
                fees = getattr(acq, custom_method_name)(amount, currency_id, country_id)
                extra_fees[acq] = fees
        return extra_fees

    def get_form_action_url(self):
        """ Returns the form action URL, for form-based acquirer implementations. """
        if hasattr(self, '%s_get_form_action_url' % self.provider):
            return getattr(self, '%s_get_form_action_url' % self.provider)()
        return False

    def _get_available_payment_input(self, partner=None, company=None):
        """ Generic (model) method that fetches available payment mechanisms
        to use in all portal / eshop pages that want to use the payment form.

        It contains

         * acquirers: record set of both form and s2s acquirers;
         * pms: record set of stored credit card data (aka payment.token)
                connected to a given partner to allow customers to reuse them """
        if not company:
            company = self.env.company
        if not partner:
            partner = self.env.user.partner_id

        domain = expression.AND([
            ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', company.id)],
            ['|', ('country_ids', '=', False), ('country_ids', 'in', [partner.country_id.id])]
        ])
        active_acquirers = self.search(domain)
        acquirers = active_acquirers.filtered(lambda acq: (acq.payment_flow == 'form' and acq.view_template_id) or
                                                               (acq.payment_flow == 's2s' and acq.registration_view_template_id))
        return {
            'acquirers': acquirers,
            'pms': self.env['payment.token'].search([
                ('partner_id', '=', partner.id),
                ('acquirer_id', 'in', acquirers.ids)]),
        }

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

        if not self.view_template_id:
            return None

        values.setdefault('return_url', '/payment/process')
        # reference and amount
        values.setdefault('reference', reference)
        amount = float_round(amount, 2)
        values.setdefault('amount', amount)

        # currency id
        currency_id = values.setdefault('currency_id', currency_id)
        if currency_id:
            currency = self.env['res.currency'].browse(currency_id)
        else:
            currency = self.env.company.currency_id
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
                'partner_country_id': partner.country_id.id or self.env['res.company']._company_default_get().country_id.id,
                'partner_country': partner.country_id,
                'partner_phone': partner.phone,
                'partner_state': partner.state_id,
                'billing_partner': billing_partner,
                'billing_partner_id': billing_partner_id,
                'billing_partner_name': billing_partner.name,
                'billing_partner_commercial_company_name': billing_partner.commercial_company_name,
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

        _logger.info('payment.acquirer.render: <%s> values rendered for form payment:\n%s', self.provider, pprint.pformat(values))
        return self.view_template_id._render(values, engine='ir.qweb')

    def get_s2s_form_xml_id(self):
        if self.registration_view_template_id:
            model_data = self.env['ir.model.data'].search([('model', '=', 'ir.ui.view'), ('res_id', '=', self.registration_view_template_id.id)])
            return ('%s.%s') % (model_data.module, model_data.name)
        return False

    def s2s_process(self, data):
        cust_method_name = '%s_s2s_form_process' % (self.provider)
        if not self.s2s_validate(data):
            return False
        if hasattr(self, cust_method_name):
            # As this method may be called in JSON and overridden in various addons
            # let us raise interesting errors before having stranges crashes
            if not data.get('partner_id'):
                raise ValueError(_('Missing partner reference when trying to create a new payment token'))
            method = getattr(self, cust_method_name)
            return method(data)
        return True

    def s2s_validate(self, data):
        cust_method_name = '%s_s2s_form_validate' % (self.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(data)
        return True

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
        "Image", help="This field holds the image used for this payment icon, limited to 1024x1024px")

    image_payment_form = fields.Binary(
        "Image displayed on the payment form", attachment=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'image' in vals:
                image = ustr(vals['image'] or '').encode('utf-8')
                vals['image_payment_form'] = image_process(image, size=(45,30))
                vals['image'] = image_process(image, size=(64,64))
        return super(PaymentIcon, self).create(vals_list)

    def write(self, vals):
        if 'image' in vals:
            image = ustr(vals['image'] or '').encode('utf-8')
            vals['image_payment_form'] = image_process(image, size=(45,30))
            vals['image'] = image_process(image, size=(64,64))
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
    _description = 'Payment Transaction'
    _order = 'id desc'
    _rec_name = 'reference'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _get_default_partner_country_id(self):
        return self.env.company.country_id.id

    date = fields.Datetime('Validation Date', readonly=True)
    acquirer_id = fields.Many2one('payment.acquirer', string='Acquirer', readonly=True, required=True)
    provider = fields.Selection(string='Provider', related='acquirer_id.provider', readonly=True)
    type = fields.Selection([
        ('validation', 'Validation of the bank card'),
        ('server2server', 'Server To Server'),
        ('form', 'Form'),
        ('form_save', 'Form with tokenization')], 'Type',
        default='form', required=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
        ('error', 'Error'),],
        string='Status', copy=False, default='draft', required=True, readonly=True)
    state_message = fields.Text(string='Message', readonly=True,
                                help='Field used to store error and/or validation messages for information')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, readonly=True)
    fees = fields.Monetary(string='Fees', currency_field='currency_id', readonly=True,
                           help='Fees amount; set by the system because depends on the acquirer')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True)
    reference = fields.Char(string='Reference', required=True, readonly=True, index=True,
                            help='Internal reference of the TX')
    acquirer_reference = fields.Char(string='Acquirer Reference', readonly=True, help='Reference of the TX as stored in the acquirer database')
    # duplicate partner / transaction data to store the values at transaction time
    partner_id = fields.Many2one('res.partner', 'Customer')
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

    # Fields used for user redirection & payment post processing
    return_url = fields.Char('Return URL after payment')
    is_processed = fields.Boolean('Has the payment been post processed', default=False)

    # Fields used for payment.transaction traceability.

    payment_token_id = fields.Many2one('payment.token', 'Payment Token', readonly=True,
                                       domain="[('acquirer_id', '=', acquirer_id)]")

    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    invoice_ids = fields.Many2many('account.move', 'account_invoice_transaction_rel', 'transaction_id', 'invoice_id',
        string='Invoices', copy=False, readonly=True,
        domain=[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'))])
    invoice_ids_nbr = fields.Integer(compute='_compute_invoice_ids_nbr', string='# of Invoices')

    _sql_constraints = [
        ('reference_uniq', 'unique(reference)', 'Reference must be unique!'),
    ]

    @api.depends('invoice_ids')
    def _compute_invoice_ids_nbr(self):
        for trans in self:
            trans.invoice_ids_nbr = len(trans.invoice_ids)

    def _create_payment(self, add_payment_vals={}):
        ''' Create an account.payment record for the current payment.transaction.
        If the transaction is linked to some invoices, the reconciliation will be done automatically.
        :param add_payment_vals:    Optional additional values to be passed to the account.payment.create method.
        :return:                    An account.payment record.
        '''
        self.ensure_one()

        payment_vals = {
            'amount': self.amount,
            'payment_type': 'inbound' if self.amount > 0 else 'outbound',
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_type': 'customer',
            'journal_id': self.acquirer_id.journal_id.id,
            'company_id': self.acquirer_id.company_id.id,
            'payment_method_id': self.env.ref('payment.account_payment_method_electronic_in').id,
            'payment_token_id': self.payment_token_id and self.payment_token_id.id or None,
            'payment_transaction_id': self.id,
            'ref': self.reference,
            **add_payment_vals,
        }
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # Track the payment to make a one2one.
        self.payment_id = payment

        if self.invoice_ids:
            self.invoice_ids.filtered(lambda move: move.state == 'draft')._post()

            (payment.line_ids + self.invoice_ids.line_ids)\
                .filtered(lambda line: line.account_id == payment.destination_account_id and not line.reconciled)\
                .reconcile()

        return payment

    def get_last_transaction(self):
        transactions = self.filtered(lambda t: t.state != 'draft')
        return transactions and transactions[0] or transactions

    def _get_processing_info(self):
        """ Extensible method for providers if they need specific fields/info regarding a tx in the payment processing page. """
        return dict()

    def _get_payment_transaction_sent_message(self):
        self.ensure_one()
        if self.payment_token_id:
            message = _('A transaction %s with %s initiated using %s credit card.')
            message_vals = (self.reference, self.acquirer_id.name, self.payment_token_id.name)
        elif self.provider in ('manual', 'transfer'):
            message = _('The customer has selected %s to pay this document.')
            message_vals = (self.acquirer_id.name)
        else:
            message = _('A transaction %s with %s initiated.')
            message_vals = (self.reference, self.acquirer_id.name)
        if self.provider not in ('manual', 'transfer'):
            message += ' ' + _('Waiting for payment confirmation...')
        return message % message_vals

    def _get_payment_transaction_received_message(self):
        self.ensure_one()
        amount = formatLang(self.env, self.amount, currency_obj=self.currency_id)
        message_vals = [self.reference, self.acquirer_id.name, amount]
        if self.state == 'pending':
            message = _('The transaction %s with %s for %s is pending.')
        elif self.state == 'authorized':
            message = _('The transaction %s with %s for %s has been authorized. Waiting for capture...')
        elif self.state == 'done':
            message = _('The transaction %s with %s for %s has been confirmed. The related payment is posted: %s')
            message_vals.append(self.payment_id._get_payment_chatter_link())
        elif self.state == 'cancel' and self.state_message:
            message = _('The transaction %s with %s for %s has been cancelled with the following message: %s')
            message_vals.append(self.state_message)
        elif self.state == 'error' and self.state_message:
            message = _('The transaction %s with %s for %s has return failed with the following error message: %s')
            message_vals.append(self.state_message)
        else:
            message = _('The transaction %s with %s for %s has been cancelled.')
        return message % tuple(message_vals)

    def _log_payment_transaction_sent(self):
        '''Log the message saying the transaction has been sent to the remote server to be
        processed by the acquirer.
        '''
        for trans in self:
            post_message = trans._get_payment_transaction_sent_message()
            for inv in trans.invoice_ids:
                inv.message_post(body=post_message)

    def _log_payment_transaction_received(self):
        '''Log the message saying a response has been received from the remote server and some
        additional informations like the old/new state, the reference of the payment... etc.
        :param old_state:       The state of the transaction before the response.
        :param add_messages:    Optional additional messages to log like the capture status.
        '''
        for trans in self.filtered(lambda t: t.provider not in ('manual', 'transfer')):
            post_message = trans._get_payment_transaction_received_message()
            for inv in trans.invoice_ids:
                inv.message_post(body=post_message)

    def _filter_transaction_state(self, allowed_states, target_state):
        """Divide a set of transactions according to their state.

        :param tuple(string) allowed_states: tuple of allowed states for the target state (strings)
        :param string target_state: target state for the filtering
        :return: tuple of transactions divided by their state, in that order
                    tx_to_process: tx that were in the allowed states
                    tx_already_processed: tx that were already in the target state
                    tx_wrong_state: tx that were not in the allowed state for the transition
        :rtype: tuple(recordset)
        """
        tx_to_process = self.filtered(lambda tx: tx.state in allowed_states)
        tx_already_processed = self.filtered(lambda tx: tx.state == target_state)
        tx_wrong_state = self -tx_to_process - tx_already_processed
        return (tx_to_process, tx_already_processed, tx_wrong_state)

    def _set_transaction_pending(self):
        '''Move the transaction to the pending state(e.g. Wire Transfer).'''
        allowed_states = ('draft',)
        target_state = 'pending'
        (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
        for tx in tx_already_processed:
            _logger.info('Trying to write the same state twice on tx (ref: %s, state: %s' % (tx.reference, tx.state))
        for tx in tx_wrong_state:
            _logger.warning('Processed tx with abnormal state (ref: %s, target state: %s, previous state %s, expected previous states: %s)' % (tx.reference, target_state, tx.state, allowed_states))

        tx_to_process.write({
            'state': target_state,
            'date': fields.Datetime.now(),
            'state_message': '',
        })
        tx_to_process._log_payment_transaction_received()

    def _set_transaction_authorized(self):
        '''Move the transaction to the authorized state(e.g. Authorize).'''
        allowed_states = ('draft', 'pending')
        target_state = 'authorized'
        (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
        for tx in tx_already_processed:
            _logger.info('Trying to write the same state twice on tx (ref: %s, state: %s' % (tx.reference, tx.state))
        for tx in tx_wrong_state:
            _logger.warning('Processed tx with abnormal state (ref: %s, target state: %s, previous state %s, expected previous states: %s)' % (tx.reference, target_state, tx.state, allowed_states))
        tx_to_process.write({
            'state': target_state,
            'date': fields.Datetime.now(),
            'state_message': '',
        })
        tx_to_process._log_payment_transaction_received()

    def _set_transaction_done(self):
        '''Move the transaction's payment to the done state(e.g. Paypal).'''
        allowed_states = ('draft', 'authorized', 'pending', 'error')
        target_state = 'done'
        (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
        for tx in tx_already_processed:
            _logger.info('Trying to write the same state twice on tx (ref: %s, state: %s' % (tx.reference, tx.state))
        for tx in tx_wrong_state:
            _logger.warning('Processed tx with abnormal state (ref: %s, target state: %s, previous state %s, expected previous states: %s)' % (tx.reference, target_state, tx.state, allowed_states))

        tx_to_process.write({
            'state': target_state,
            'date': fields.Datetime.now(),
            'state_message': '',
        })

    def _reconcile_after_transaction_done(self):
        # Validate invoices automatically upon the transaction is posted.
        invoices = self.mapped('invoice_ids').filtered(lambda inv: inv.state == 'draft')
        invoices._post()

        # Create & Post the payments.
        for trans in self:
            if trans.payment_id:
                continue

            trans._create_payment()

    def _set_transaction_cancel(self):
        '''Move the transaction's payment to the cancel state(e.g. Paypal).'''
        allowed_states = ('draft', 'authorized')
        target_state = 'cancel'
        (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
        for tx in tx_already_processed:
            _logger.info('Trying to write the same state twice on tx (ref: %s, state: %s' % (tx.reference, tx.state))
        for tx in tx_wrong_state:
            _logger.warning('Processed tx with abnormal state (ref: %s, target state: %s, previous state %s, expected previous states: %s)' % (tx.reference, target_state, tx.state, allowed_states))

        # Cancel the existing payments.
        tx_to_process.mapped('payment_id').action_cancel()

        tx_to_process.write({'state': target_state, 'date': fields.Datetime.now()})
        tx_to_process._log_payment_transaction_received()

    def _set_transaction_error(self, msg):
        '''Move the transaction to the error state (Third party returning error e.g. Paypal).'''
        allowed_states = ('draft', 'authorized', 'pending')
        target_state = 'error'
        (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
        for tx in tx_already_processed:
            _logger.info('Trying to write the same state twice on tx (ref: %s, state: %s' % (tx.reference, tx.state))
        for tx in tx_wrong_state:
            _logger.warning('Processed tx with abnormal state (ref: %s, target state: %s, previous state %s, expected previous states: %s)' % (tx.reference, target_state, tx.state, allowed_states))

        tx_to_process.write({
            'state': target_state,
            'date': fields.Datetime.now(),
            'state_message': msg,
        })
        self._log_payment_transaction_received()

    def _post_process_after_done(self):
        self._reconcile_after_transaction_done()
        self._log_payment_transaction_received()
        self.write({'is_processed': True})
        return True

    def _cron_post_process_after_done(self):
        if not self:
            ten_minutes_ago = datetime.now() - relativedelta.relativedelta(minutes=10)
            # we don't want to forever try to process a transaction that doesn't go through
            retry_limit_date = datetime.now() - relativedelta.relativedelta(days=2)
            # we retrieve all the payment tx that need to be post processed
            self = self.search([('state', '=', 'done'),
                                ('is_processed', '=', False),
                                ('date', '<=', ten_minutes_ago),
                                ('date', '>=', retry_limit_date),
                            ])
        for tx in self:
            try:
                tx._post_process_after_done()
                self.env.cr.commit()
            except Exception as e:
                _logger.exception("Transaction post processing failed")
                self.env.cr.rollback()

    @api.model
    def _compute_reference_prefix(self, values):
        if values and values.get('invoice_ids'):
            invoices = self.new({'invoice_ids': values['invoice_ids']}).invoice_ids
            return ','.join(invoices.mapped('name'))
        return None

    @api.model
    def _compute_reference(self, values=None, prefix=None):
        '''Compute a unique reference for the transaction.
        If prefix:
            prefix-\d+
        If some invoices:
            <inv_number_0>.number,<inv_number_1>,...,<inv_number_n>-x
        If some sale orders:
            <so_name_0>.number,<so_name_1>,...,<so_name_n>-x
        Else:
            tx-\d+
        :param values: values used to create a new transaction.
        :param prefix: custom transaction prefix.
        :return: A unique reference for the transaction.
        '''
        if not prefix:
            prefix = self._compute_reference_prefix(values)
            if not prefix:
                prefix = 'tx'

        # Fetch the last reference
        # E.g. If the last reference is SO42-5, this query will return '-5'
        self._cr.execute('''
                SELECT CAST(SUBSTRING(reference FROM '-\d+$') AS INTEGER) AS suffix
                FROM payment_transaction WHERE reference LIKE %s ORDER BY suffix
            ''', [prefix + '-%'])
        query_res = self._cr.fetchone()
        if query_res:
            # Increment the last reference by one
            suffix = '%s' % (-query_res[0] + 1)
        else:
            # Start a new indexing from 1
            suffix = '1'

        return '%s-%s' % (prefix, suffix)

    def action_view_invoices(self):
        action = {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'target': 'current',
        }
        invoice_ids = self.invoice_ids.ids
        if len(invoice_ids) == 1:
            invoice = invoice_ids[0]
            action['res_id'] = invoice
            action['view_mode'] = 'form'
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', invoice_ids)]
        return action

    @api.constrains('state', 'acquirer_id')
    def _check_authorize_state(self):
        failed_tx = self.filtered(lambda tx: tx.state == 'authorized' and tx.acquirer_id.provider not in self.env['payment.acquirer']._get_feature_support()['authorize'])
        if failed_tx:
            raise exceptions.ValidationError(_('The %s payment acquirers are not allowed to manual capture mode!', failed_tx.mapped('acquirer_id.name')))

    @api.model
    def create(self, values):
        # call custom create method if defined
        acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        if values.get('partner_id'):
            partner = self.env['res.partner'].browse(values['partner_id'])

            values.update({
                'partner_name': partner.name,
                'partner_lang': partner.lang or self.env.user.lang,
                'partner_email': partner.email,
                'partner_zip': partner.zip,
                'partner_address': _partner_format_address(partner.street or '', partner.street2 or ''),
                'partner_city': partner.city,
                'partner_country_id': partner.country_id.id or self._get_default_partner_country_id(),
                'partner_phone': partner.phone,
            })

        # compute fees
        custom_method_name = '%s_compute_fees' % acquirer.provider
        if hasattr(acquirer, custom_method_name):
            fees = getattr(acquirer, custom_method_name)(
                values.get('amount', 0.0), values.get('currency_id'), values.get('partner_country_id', self._get_default_partner_country_id()))
            values['fees'] = fees

        # custom create
        custom_method_name = '%s_create' % acquirer.provider
        if hasattr(self, custom_method_name):
            values.update(getattr(self, custom_method_name)(values))

        if not values.get('reference'):
            values['reference'] = self._compute_reference(values=values)

        # Default value of reference is
        tx = super(PaymentTransaction, self).create(values)

        # Generate callback hash if it is configured on the tx; avoid generating unnecessary stuff
        # (limited sudo env for checking callback presence, must work for manual transactions too)
        tx_sudo = tx.sudo()
        if tx_sudo.callback_model_id and tx_sudo.callback_res_id and tx_sudo.callback_method:
            tx.write({'callback_hash': tx._generate_callback_hash()})

        return tx

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

    def s2s_do_transaction(self, **kwargs):
        custom_method_name = '%s_s2s_do_transaction' % self.acquirer_id.provider
        for trans in self:
            trans._log_payment_transaction_sent()
            if hasattr(trans, custom_method_name):
                return getattr(trans, custom_method_name)(**kwargs)

    def s2s_do_refund(self, **kwargs):
        custom_method_name = '%s_s2s_do_refund' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    def s2s_capture_transaction(self, **kwargs):
        custom_method_name = '%s_s2s_capture_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    def s2s_void_transaction(self, **kwargs):
        custom_method_name = '%s_s2s_void_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    def s2s_get_tx_status(self):
        """ Get the tx status. """
        invalid_param_method_name = '_%s_s2s_get_tx_status' % self.acquirer_id.provider
        if hasattr(self, invalid_param_method_name):
            return getattr(self, invalid_param_method_name)()
        return True

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

    def action_capture(self):
        if any(t.state != 'authorized' for t in self):
            raise ValidationError(_('Only transactions having the authorized status can be captured.'))
        for tx in self:
            tx.s2s_capture_transaction()

    def action_void(self):
        if any(t.state != 'authorized' for t in self):
            raise ValidationError(_('Only transactions having the capture status can be voided.'))
        for tx in self:
            tx.s2s_void_transaction()


class PaymentToken(models.Model):
    _name = 'payment.token'
    _order = 'partner_id, id desc'
    _description = 'Payment Token'

    name = fields.Char('Name', help='Name of the payment token')
    short_name = fields.Char('Short name', compute='_compute_short_name')
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    acquirer_id = fields.Many2one('payment.acquirer', 'Acquirer Account', required=True)
    company_id = fields.Many2one(related='acquirer_id.company_id', store=True, index=True)
    acquirer_ref = fields.Char('Acquirer Ref.', required=True)
    active = fields.Boolean('Active', default=True)
    payment_ids = fields.One2many('payment.transaction', 'payment_token_id', 'Payment Transactions')
    verified = fields.Boolean(string='Verified', default=False)

    @api.model
    def create(self, values):
        # call custom create method if defined
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

        reference = "VALIDATION-%s-%s" % (self.id, datetime.now().strftime('%y%m%d_%H%M%S'))
        tx = self.env['payment.transaction'].sudo().create({
            'amount': amount,
            'acquirer_id': self.acquirer_id.id,
            'type': 'validation',
            'currency_id': currency.id,
            'reference': reference,
            'payment_token_id': self.id,
            'partner_id': self.partner_id.id,
            'partner_country_id': self.partner_id.country_id.id,
            'state_message': _('This Transaction was automatically processed & refunded in order to validate a new credit card.'),
        })

        kwargs.update({'3d_secure': True})
        tx.s2s_do_transaction(**kwargs)

        # if 3D secure is called, then we do not refund right now
        if not tx.html_3ds:
            tx.s2s_do_refund()

        return tx

    @api.depends('name')
    def _compute_short_name(self):
        for token in self:
            token.short_name = token.name.replace('XXXXXXXXXXXX', '***')

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
