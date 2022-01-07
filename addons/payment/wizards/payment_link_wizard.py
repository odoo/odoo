# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
    has_multiple_acquirers = fields.Boolean(
        string="Has Multiple Acquirers",
        compute='_compute_has_multiple_acquirers',
    )
    payment_acquirer_selection = fields.Selection(
        string="Allow Payment Acquirer",
        help="If a specific payment acquirer is selected, customers will only be allowed to pay "
             "via this one. If 'All' is selected, customers can pay via any available payment "
             "acquirer.",
        selection='_selection_payment_acquirer_selection',
        default='all',
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
            link.available_acquirer_ids = link._get_payment_acquirer_available(
                res_model=link.res_model,
                res_id=link.res_id,
                company_id=link.company_id.id,
                partner_id=link.partner_id.id,
                amount=link.amount,
                currency_id=link.currency_id.id,
            )

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
            selection.extend(
                self._get_payment_acquirer_available(
                    res_model=res_model,
                    res_id=res_id,
                    company_id=company_id.id,
                    partner_id=partner_id.id,
                    amount=related_document.amount_total,
                    currency_id=currency_id.id,
                ).name_get()
            )
        return selection

    def _get_payment_acquirer_available(self, **kwargs):
        """ Select and return the acquirers matching the criteria.

        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        return self.env['payment.acquirer'].sudo()._get_compatible_acquirers(**kwargs)

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
