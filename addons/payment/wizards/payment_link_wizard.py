# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from odoo.addons.payment import utils as payment_utils


class PaymentLinkWizard(models.TransientModel):
    _name = "payment.link.wizard"
    _description = "Generate Payment Link"

    @api.model
    def default_get(self, fields):
        res = super(PaymentLinkWizard, self).default_get(fields)
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')
        res.update({'res_id': res_id, 'res_model': res_model})
        amount_field = 'amount_residual' if res_model == 'account.move' else 'amount_total'
        if res_id and res_model == 'account.move':
            record = self.env[res_model].browse(res_id)
            res.update({
                'description': record.payment_reference,
                'amount': record[amount_field],
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'amount_max': record[amount_field],
            })
        return res

    @api.model
    def fields_view_get(self, *args, **kwargs):
        """ Overrides orm fields_view_get

        Using a Many2One field, when a user opens this wizard and tries to select a preferred
        payment acquirer, he will get an AccessError telling that he is not allowed to access
        'payment.acquirer' records. This error is thrown because the Many2One field is filled
        by the name_get() function and users don't have clearance to read 'payment.acquirer' records.

        This override allows replacing the Many2One with a selection field, that is prefilled in the
        backend with the name of available acquirers. Therefore, Users will be able to select their
        preferred acquirer.

        :return: composition of the requested view (including inherited views and extensions)
        :rtype: dict
        """
        res = super().fields_view_get(*args, **kwargs)
        if res['type'] == 'form':
            doc = etree.XML(res['arch'])

            # Replace acquirer_id with payment_acquirer_selection in the view
            acq = doc.xpath("//field[@name='acquirer_id']")[0]
            acq.attrib['name'] = 'payment_acquirer_selection'
            acq.attrib['widget'] = 'selection'
            acq.attrib['string'] = 'Force Payment Acquirer'
            del acq.attrib['options']
            del acq.attrib['placeholder']

            # Replace acquirer_id with payment_acquirer_selection in the fields list
            xarch, xfields = self.env['ir.ui.view'].postprocess_and_fields(doc, model=self._name)

            res['arch'] = xarch
            res['fields'] = xfields
        return res

    res_model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    amount_max = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')
    partner_email = fields.Char(related='partner_id.email')
    link = fields.Char(string='Payment Link', compute='_compute_values')
    description = fields.Char('Payment Ref')
    access_token = fields.Char(compute='_compute_values')
    company_id = fields.Many2one('res.company', compute='_compute_company')
    available_acquirer_ids = fields.Many2many(
        comodel_name='payment.acquirer',
        string="Payment Acquirers Available",
        compute='_compute_available_acquirer_ids',
        compute_sudo=True,
    )
    acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        string="Force Payment Acquirer",
        domain="[('id', 'in', available_acquirer_ids)]",
        help="Force the customer to pay via the specified payment acquirer. Leave empty to allow the customer to choose among all acquirers."
    )
    has_multiple_acquirers = fields.Boolean(
        string="Has Multiple Acquirers",
        compute='_compute_has_multiple_acquirers',
    )
    payment_acquirer_selection = fields.Selection(
        string="Payment acquirer selected",
        selection='_selection_payment_acquirer_selection',
        default='all',
        compute='_compute_payment_acquirer_selection',
        inverse='_inverse_payment_acquirer_selection',
        required=True,
    )

    @api.onchange('amount', 'description')
    def _onchange_amount(self):
        if float_compare(self.amount_max, self.amount, precision_rounding=self.currency_id.rounding or 0.01) == -1:
            raise ValidationError(_("Please set an amount smaller than %s.") % (self.amount_max))
        if self.amount <= 0:
            raise ValidationError(_("The value of the payment amount must be positive."))

    @api.depends('amount', 'description', 'partner_id', 'currency_id', 'payment_acquirer_selection')
    def _compute_values(self):
        for payment_link in self:
            payment_link.access_token = payment_utils.generate_access_token(
                payment_link.partner_id.id, payment_link.amount, payment_link.currency_id.id
            )
        # must be called after token generation, obvsly - the link needs an up-to-date token
        self._generate_link()

    @api.depends('res_model', 'res_id')
    def _compute_company(self):
        for link in self:
            record = self.env[link.res_model].browse(link.res_id)
            link.company_id = record.company_id if 'company_id' in record else False

    @api.depends('company_id', 'partner_id', 'currency_id')
    def _compute_available_acquirer_ids(self):
        for link in self:
            link.available_acquirer_ids = link._get_payment_acquirer_available()

    @api.depends('acquirer_id')
    def _compute_payment_acquirer_selection(self):
        for link in self:
            link.payment_acquirer_selection = link.acquirer_id.id if link.acquirer_id else 'all'

    def _inverse_payment_acquirer_selection(self):
        for link in self:
            link.acquirer_id = link.payment_acquirer_selection if link.payment_acquirer_selection != 'all' else False

    def _selection_payment_acquirer_selection(self):
        """ Specify available acquirers in the selection field.
        :return: The selection list of available acquirers.
        :rtype: list[tuple]
        """
        defaults = self.default_get(['res_model', 'res_id'])
        selection = [('all', "All")]
        res_model, res_id = defaults['res_model'], defaults['res_id']
        if res_id and res_model in ['account.move', "sale.order"]:
            # At module install, the selection method is called
            # but the document context isn't specified.
            related_document = self.env[res_model].browse(res_id)
            company_id = related_document.company_id
            partner_id = related_document.partner_id
            currency_id = related_document.currency_id
            if res_model == "sale.order":
                # If the Order contains a recurring product but is not already linked to a
                # subscription, the payment acquirer must support tokenization. The res_id allows
                # the overrides of sale_subscription to check this condition.
                selection.extend(
                    self._get_payment_acquirer_available(
                        company_id.id, partner_id.id, currency_id.id, res_id,
                    ).name_get()
                )
            else:
                selection.extend(
                    self._get_payment_acquirer_available(
                        company_id.id, partner_id.id, currency_id.id,
                    ).name_get()
                )
        return selection

    def _get_payment_acquirer_available(self, company_id=None, partner_id=None, currency_id=None):
        """ Select and return the acquirers matching the criteria.

        :param int company_id: The company to which acquirers must belong, as a `res.company` id
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param int currency_id: The payment currency if known beforehand, as a `res.currency` id
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        return self.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            company_id=company_id or self.company_id.id,
            partner_id=partner_id or self.partner_id.id,
            currency_id=currency_id or self.currency_id.id
        )

    @api.depends('available_acquirer_ids')
    def _compute_has_multiple_acquirers(self):
        for link in self:
            link.has_multiple_acquirers = len(link.available_acquirer_ids) > 1

    def _generate_link(self):
        for payment_link in self:
            related_document = self.env[payment_link.res_model].browse(payment_link.res_id)
            base_url = related_document.get_base_url()  # Don't generate links for the wrong website
            payment_link.link = f'{base_url}/payment/pay' \
                   f'?reference={urls.url_quote(payment_link.description)}' \
                   f'&amount={payment_link.amount}' \
                   f'&currency_id={payment_link.currency_id.id}' \
                   f'&partner_id={payment_link.partner_id.id}' \
                   f'&company_id={payment_link.company_id.id}' \
                   f'&invoice_id={payment_link.res_id}' \
                   f'{"&acquirer_id=" + str(payment_link.payment_acquirer_selection) if payment_link.payment_acquirer_selection != "all" else "" }' \
                   f'&access_token={payment_link.access_token}'
