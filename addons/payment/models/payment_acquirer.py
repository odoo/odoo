# -*- coding: utf-'8' "-*-"
import logging

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


def _partner_format_address(address1=False, address2=False):
    return ' '.join((address1 or '', address2 or '')).strip()


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


class ValidationError(ValueError):
    """ Used for value error when validating transaction data coming from acquirers. """
    pass


class PaymentAcquirer(models.Model):
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
    Odoo and the acquirer. It generally consists in return urls given to the
    button form and that the acquirer uses to send the customer back after the
    transaction, with transaction details given as a POST request.
    """
    _name = 'payment.acquirer'
    _description = 'Payment Acquirer'
    _order = 'sequence'

    @api.model
    def _get_providers(self):
        return [('manual', 'Manual Configuration')]

    # indirection to ease inheritance
    _provider_selection = lambda self: self._get_providers()

    name = fields.Char(required=True, translate=True)
    provider = fields.Selection(_provider_selection, required=True, default='manual')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True)
    pre_msg = fields.Html('Help Message', translate=True,
                          help='Message displayed to explain and help the payment process.')
    post_msg = fields.Html('Thanks Message',  translate=True,
                           help='Message displayed after having done the payment process.')
    view_template_id = fields.Many2one('ir.ui.view', string='Form Button Template', required=True)
    registration_view_template_id = fields.Many2one('ir.ui.view', string='S2S Form Template',
                                                    domain=[('type', '=', 'qweb')],
                                                    help="Template for method registration")
    environment = fields.Selection(
        [('test', 'Test'), ('prod', 'Production')],
        oldname='env', default='test')
    website_published = fields.Boolean(
        'Visible in Portal / Website', copy=False,
        help="Make this payment acquirer available (Customer invoices, etc.)"),
    auto_confirm = fields.Selection(
        [('none', 'No automatic confirmation'),
         ('at_pay_confirm', 'At payment with acquirer confirmation'),
         ('at_pay_now', 'At payment no acquirer confirmation needed')],
        string='Order Confirmation', default='at_pay_confirm', required=True)
    pending_msg = fields.Html(string='Pending Message', translate=True,
        default="<i>Pending,</i> Your online payment has been successfully processed. But your order is not validated yet.",
        help='Message displayed, if order is in pending state after having done the payment process.')
    done_msg = fields.Html(string='Done Message', translate=True,
        default="<i>Done,</i> Your online payment has been successfully processed. Thank you for your order.",
        help='Message displayed, if order is done successfully after having done the payment process.')
    cancel_msg = fields.Html(string='Cancel Message', translate=True,
        default="<i>Cancel,</i> Your payment has been cancelled.",
        help='Message displayed, if order is cancel during the payment process.')
    error_msg = fields.Html(string='Error Message', translate=True,
        default="<i>Error,</i> Please be aware that an error occurred during the transaction. The order has been confirmed but won't be paid. Don't hesitate to contact us if you have any questions on the status of your order.",
        help='Message displayed, if error is occur during the payment process.')
    # Fees
    fees_active = fields.Boolean(string='Add Extra Fees')
    fees_dom_fixed = fields.Float(string='Fixed Domestic Fees')
    fees_dom_var = fields.Float(string='Variable Domestic Fees (in percents)')
    fees_int_fixed = fields.Float(string='Fixed International Fees')
    fees_int_var = fields.Float(string='Variable International Fees (in percents)')
    sequence = fields.Integer(help="Determine the display order")
        'module_id': fields.many2one('ir.module.module', string='Corresponding Module'),
        'module_state': fields.related('module_id', 'state', type='char', string='Installation State'),
        'description': fields.html('Description'),

    image = fields.Binary("Image", attachment=True,
        help="This field holds the image used for this provider, limited to 1024x1024px")
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of this provider. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of this provider. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")


    @api.constrains('provider')
    def _check_required_if_provider(self):
        """ If the field has 'required_if_provider="<provider>"' attribute, then it
        required if record.provider is <provider>. """
        for acquirer in self:
            if any(getattr(field, 'required_if_provider', None) == acquirer.provider and not acquirer[key] for key, field in self._fields.items()):
                raise ValidationError(_('Required fields not filled, ["required for this provider"]'))
        return True

    @api.multi
    def get_form_action_url(self):
    @openerp.api.model
    def create(self, vals):
        image_resize_images(vals)
        return super(PaymentAcquirer, self).create(vals)

    @openerp.api.multi
    def write(self, vals):
        image_resize_images(vals)
        return super(PaymentAcquirer, self).write(vals)

        """ Returns the form action URL, for form-based acquirer implementations. """
        self.ensure_one()
        if hasattr(self, '%s_get_form_action_url' % self.provider):
            action_url = getattr(self, '%s_get_form_action_url' % self.provider)()
            return action_url[0] if isinstance(action_url, list) else action_url  # We need to check list or not because old API returns list
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
        :param dict context: Odoo context

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
         - context: Odoo context dictionary

        """
        self.ensure_one()
        # reference and amount
        values.setdefault('reference', reference)
        amount = tools.float_round(amount, 2)
        values.setdefault('amount', amount)

        # currency id
        currency_id = values.setdefault('currency_id', currency_id)
        if currency_id:
            currency = self.env['res.currency'].browse(currency_id)
        else:
            currency = self.env.user.company_id.currency_id
        values['currency'] = currency

        # Fill partner_* using values['partner_id'] or partner_id arguement
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
            values['country'] = self.env['res.country'].browse(values['partner_country_id'])
        if not values.get('billing_partner_address'):
            values['billing_address'] = _partner_format_address(values.get('billing_partner_street', ''), values.get('billing_partner_street2', ''))
        if not values.get('billing_partner_country') and values.get('billing_partner_country_id'):
            values['billing_country'] = self.env['res.country'].browse(values.get('billing_partner_country_id'))

        # compute fees
        fees_method_name = '%s_compute_fees' % self.provider
        if hasattr(self, fees_method_name):
            fees = getattr(self, fees_method_name)(values['amount'], values['currency_id'], values['partner_country_id'])
            final_fees = fees[0] if isinstance(fees, list) else fees  # We need to check list or not because old API returns
            values['fees'] = tools.float_round(final_fees, 2)

        # call <name>_form_generate_values to update the tx dict with acqurier specific values
        cust_method_name = '%s_form_generate_values' % (self.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            inv_type = method(values)
            values = inv_type[0] if isinstance(inv_type, list) else inv_type  # We need to check list or not because old API returns list

        values.update({
            'tx_url': self.env.context.get('tx_url', self.get_form_action_url()),
            'submit_class': self.env.context.get('submit_class', 'btn btn-link'),
            'submit_txt': self.env.context.get('submit_txt'),
            'acquirer': self,
            'user': self.env.user,
            'context': self.env.context,
            'type': values.get('type') or 'form',
        })
        values.setdefault('return_url', False)

        return self.view_template_id.render(values, engine='ir.qweb')

    def _registration_render(self, partner_id, values=None):
        if values is None:
            values = {}
        values.update(id=self.id, partner_id=partner_id)
        method_name = '_%s_registration_form_generate_values' % (self.provider)
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            values.update(method(values))
        return self.registration_view_template_id.render(qweb_context, engine='ir.qweb')

    @api.multi
    def s2s_process(self, data):
        self.ensure_one()
        cust_method_name = '%s_s2s_form_process' % (self.provider)
        if not self.s2s_validate(data):
            return False
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(data)
        return True

    @api.multi
    def s2s_validate(self, data):
        self.ensure_one()
        cust_method_name = '%s_s2s_form_validate' % (self.provider)
        if hasattr(self, cust_method_name):
            method = getattr(self, cust_method_name)
            return method(data)
        return True

    def toggle_enviroment_value(self, cr, uid, ids, context=None):
        acquirers = self.browse(cr, uid, ids, context=context)
        prod_ids = [acquirer.id for acquirer in acquirers if acquirer.environment == 'prod']
        test_ids = [acquirer.id for acquirer in acquirers if acquirer.environment == 'test']
        self.write(cr, uid, prod_ids, {'environment': 'test'}, context=context)
        self.write(cr, uid, test_ids, {'environment': 'prod'}, context=context)

    def button_immediate_install(self, cr, uid, ids, context=None):
        acquirer_id = self.browse(cr, uid, ids, context=context)
        if acquirer_id.module_id and acquirer_id.module_state != 'installed':
            acquirer_id.module_id.button_immediate_install()
            context['active_id'] = ids[0]
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.acquirer',
                'type': 'ir.actions.act_window',
                'res_id': ids[0],
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

     - ``<name>_form_feedback(self, cr, uid, data, context=None)``: method that
       handles the data coming from the acquirer after the transaction. It will
       generally receives data posted by the acquirer after the transaction.
    """
    _name = 'payment.transaction'
    _description = 'Payment Transaction'
    _order = 'id desc'
    _rec_name = 'reference'

    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    def _default_partner_country_id(self):
        comp = self.env['res.company'].browse(self.env.context.get('company_id', 1))
        return comp.country_id.id

    create_date = fields.Datetime(string='Creation Date', readonly=True)
    date_validate = fields.Datetime(string='Validation Date')
    acquirer_id = fields.Many2one('payment.acquirer', string='Acquirer', required=True)
    type = fields.Selection([('server2server', 'Server To Server'), ('form', 'Form'), ('form_save', 'Form with credentials storage')], default="form", required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('pending', 'Pending'),
         ('done', 'Done'), ('error', 'Error'),
         ('cancel', 'Canceled')
         ], 'Status', required=True, default="draft",
        track_visibility='onchange', copy=False)
    state_message = fields.Text(string='Message', help='Field used to store error and/or validation messages for information')
    # payment
    amount = fields.Float(required=True, digits=(16, 2), track_visibility='always', help='Transaction Amount')
    fees = fields.Float(digits=(16, 2), track_visibility='always', help='Fees amount; set by the system because depends on the acquirer')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    reference = fields.Char(
        default=lambda self: self.env['ir.sequence'].next_by_code('payment.transaction'),
        required=True, help='Internal reference of the TX')
    acquirer_reference = fields.Char(help='Reference of the TX as stored in the acquirer database')
    # duplicate partner / transaction data to store the values at transaction time
    partner_id = fields.Many2one('res.partner', string='Partner', track_visibility='onchange')
    partner_name = fields.Char()
    partner_lang = fields.Selection(_lang_get, string='Language', default="en_US")
    partner_email = fields.Char(string='Email')
    partner_zip = fields.Char(string='Zip')
    partner_address = fields.Char(string='Address')
    partner_city = fields.Char(string='City')
    partner_country_id = fields.Many2one('res.country', string='Country', default=_default_partner_country_id, required=True)
    partner_phone = fields.Char(string='Phone')
    html_3ds = fields.Char(string='3D Secure HTML')

    callback_eval = fields.Char(string='S2S Callback', help="""\
        Will be safe_eval with `self` being the current transaction. i.e.:
            self.env['my.model'].payment_validated(self)""", oldname="s2s_cb_eval")
    payment_method_id = fields.Many2one('payment.method', string='Payment Method', domain="[('acquirer_id', '=', acquirer_id)]")

    @api.constrains('reference', 'state')
    def _check_reference(self):
        for transaction in self:
            if transaction.state not in ['cancel', 'error'] and self.search_count([('reference', '=', transaction.reference), ('id', '!=', transaction.id)]):
                raise ValidationError(_('The payment transaction reference must be unique!'))
            return True

    @api.model
    def create(self, values):

        if values.get('partner_id'):  # @TDENOTE: not sure
            partner = self.env['res.partner'].browse(values['partner_id'])
            values.update(self._get_partner_details(partner))

        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

            # compute fees
            custom_method_name = '%s_compute_fees' % acquirer.provider
            if hasattr(acquirer, custom_method_name):
                fees = getattr(acquirer, custom_method_name)(values.get('amount', 0.0), values.get('currency_id'), values.get('partner_country_id'))
                values['fees'] = tools.float_round(fees[0], 2)

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(values))

        # Default value of reference is
        transaction = super(PaymentTransaction, self).create(values)
        if not values.get('reference'):
            transaction.write({'reference': str(transaction.id)})
        return transaction

    @api.multi
    def write(self, values):
        Acquirer = self.env['payment.acquirer']
        if ('acquirer_id' in values or 'amount' in values) and 'fees' not in values:
            # The acquirer or the amount has changed, and the fees are not explicitely forced. Fees must be recomputed.
            for transaction in self:
                vals = dict(values)
                vals['fees'] = 0.0
                if values.get('acquirer_id'):
                    acquirer = Acquirer.browse(values['acquirer_id'])
                else:
                    acquirer = transaction.acquirer_id
                if acquirer:
                    custom_method_name = '%s_compute_fees' % acquirer.provider
                    if hasattr(Acquirer, custom_method_name):
                        amount = (values['amount'] if 'amount' in values else transaction.amount) or 0.0
                        currency_id = values.get('currency_id') or transaction.currency_id.id
                        country_id = values.get('partner_country_id') or transaction.partner_country_id.id
                        fees = getattr(Acquirer, custom_method_name)(acquirer.id, amount, currency_id, country_id)
                        vals['fees'] = tools.float_round(fees, 2)
                result = super(PaymentTransaction, self).write(vals)
            return result
        return super(PaymentTransaction, self).write(values)

    def _get_partner_details(self, partner):
        partner_details = {}
        if partner:
            partner_details = {
                'partner_name': partner.name,
                'partner_lang': partner.lang or 'en_US',
                'partner_email': partner.email,
                'partner_zip': partner.zip,
                'partner_address': _partner_format_address(partner.street, partner.street2),
                'partner_city': partner.city,
                'partner_country_id': partner.country_id.id or self._default_partner_country_id(),
                'partner_phone': partner.phone,
            }
        return partner_details

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        partner_details = self._get_partner_details(self.partner_id)
        for fname, value in partner_details.iteritems():
            setattr(self, fname, value)

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
        self.ensure_one()
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
        invalid_parameters, transaction = None, None

        tx_find_method_name = '_%s_form_get_tx_from_data' % acquirer_name
        if hasattr(self, tx_find_method_name):
            transaction = getattr(self, tx_find_method_name)(data)

        invalid_param_method_name = '_%s_form_get_invalid_parameters' % acquirer_name
        if hasattr(self, invalid_param_method_name):
            invalid_parameters = getattr(self, invalid_param_method_name)(transaction, data)

        if invalid_parameters:
            _error_message = '%s: incorrect transaction data:\n' % (acquirer_name)
            for item in invalid_parameters:
                _error_message += '\t%s: received %s instead of %s\n' % (item[0], item[1], item[2])
            _logger.error(_error_message)
            return False

        feedback_method_name = '_%s_form_validate' % acquirer_name
        if hasattr(self, feedback_method_name):
            return getattr(self, feedback_method_name)(transaction, data)

        return True

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------
    @api.multi
    def s2s_create(self, values, cc_values):
        # This method never call
        self.ensure_one()
        transaction, transaction_result = self.s2s_send(values, cc_values)
        transaction.s2s_feedback(transaction_result)
        return transaction

    @api.multi
    def s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        custom_method_name = '%s_s2s_do_transaction' % self.acquirer_id.provider
        if hasattr(self, custom_method_name):
            return getattr(self, custom_method_name)(**kwargs)

    @api.multi
    def s2s_get_tx_status(self):
        # This method never call
        """ Get the transaction status. """

        self.ensure_one()
        invalid_param_method_name = '_%s_s2s_get_tx_status' % self.acquirer_id.provider
        if hasattr(self, invalid_param_method_name):
            return getattr(self, invalid_param_method_name)(self)

        return True


class PaymentMethod(models.Model):
    _name = 'payment.method'
    _order = 'partner_id'

    name = fields.Char(help='Name of the payment method')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    acquirer_id = fields.Many2one('payment.acquirer', string='Acquirer Account', required=True)
    acquirer_ref = fields.Char(string='Acquirer Reference', required=True)
    active = fields.Boolean(default=True)
    payment_ids = fields.One2many('payment.transaction', 'payment_method_id', string='Payment Transactions')

    @api.model
    def create(self, values):
        # call custom create method if defined (i.e. ogone_create for ogone)
        if values.get('acquirer_id'):
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

            # custom create
            custom_method_name = '%s_create' % acquirer.provider
            if hasattr(self, custom_method_name):
                values.update(getattr(self, custom_method_name)(values))

        return super(PaymentMethod, self).create(values)
