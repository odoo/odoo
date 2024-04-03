# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from odoo.addons.payment import utils as payment_utils


class PaymentLinkWizard(models.TransientModel):
    _name = 'payment.link.wizard'
    _description = "Generate Payment Link"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_id = self.env.context.get('active_id')
        res_model = self.env.context.get('active_model')
        if res_id and res_model:
            res.update({'res_model': res_model, 'res_id': res_id})
            res.update(
                self.env[res_model].browse(res_id)._get_default_payment_link_values()
            )
        return res

    res_model = fields.Char("Related Document Model", required=True)
    res_id = fields.Integer("Related Document ID", required=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    amount_max = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')
    partner_email = fields.Char(related='partner_id.email')
    description = fields.Char("Payment Ref")
    link = fields.Char(string="Payment Link", compute='_compute_link')
    company_id = fields.Many2one('res.company', compute='_compute_company_id')
    available_provider_ids = fields.Many2many(
        comodel_name='payment.provider',
        string="Payment Providers Available",
        compute='_compute_available_provider_ids',
        compute_sudo=True,
    )
    has_multiple_providers = fields.Boolean(
        string="Has Multiple Providers",
        compute='_compute_has_multiple_providers',
    )
    payment_provider_selection = fields.Selection(
        string="Allow Payment Provider",
        help="If a specific payment provider is selected, customers will only be allowed to pay "
             "via this one. If 'All' is selected, customers can pay via any available payment "
             "provider.",
        selection='_selection_payment_provider_selection',
        default='all',
        required=True,
    )

    @api.onchange('amount', 'description')
    def _onchange_amount(self):
        if float_compare(self.amount_max, self.amount, precision_rounding=self.currency_id.rounding or 0.01) == -1:
            raise ValidationError(_("Please set an amount smaller than %s.", self.amount_max))
        if self.amount <= 0:
            raise ValidationError(_("The value of the payment amount must be positive."))

    @api.depends('res_model', 'res_id')
    def _compute_company_id(self):
        for link in self:
            record = self.env[link.res_model].browse(link.res_id)
            link.company_id = record.company_id if 'company_id' in record else False

    @api.depends('company_id', 'partner_id', 'currency_id')
    def _compute_available_provider_ids(self):
        for link in self:
            link.available_provider_ids = link._get_payment_provider_available(
                res_model=link.res_model,
                res_id=link.res_id,
                company_id=link.company_id.id,
                partner_id=link.partner_id.id,
                amount=link.amount,
                currency_id=link.currency_id.id,
            )

    def _selection_payment_provider_selection(self):
        """ Specify available providers in the selection field.
        :return: The selection list of available providers.
        :rtype: list[tuple]
        """
        defaults = self.default_get(['res_model', 'res_id'])
        selection = [('all', "All")]
        res_model, res_id = defaults.get('res_model'), defaults.get('res_id')
        if res_id and res_model in ['account.move', "sale.order"]:
            # At module install, the selection method is called
            # but the document context isn't specified.
            related_document = self.env[res_model].browse(res_id)
            company_id = related_document.company_id
            partner_id = related_document.partner_id
            currency_id = related_document.currency_id
            selection.extend(
                self._get_payment_provider_available(
                    res_model=res_model,
                    res_id=res_id,
                    company_id=company_id.id,
                    partner_id=partner_id.id,
                    amount=related_document.amount_total,
                    currency_id=currency_id.id,
                ).name_get()
            )
        return selection

    def _get_payment_provider_available(self, **kwargs):
        """ Select and return the providers matching the criteria.

        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        return self.env['payment.provider'].sudo()._get_compatible_providers(**kwargs)

    @api.depends('available_provider_ids')
    def _compute_has_multiple_providers(self):
        for link in self:
            link.has_multiple_providers = len(link.available_provider_ids) > 1

    def _get_access_token(self):
        self.ensure_one()
        return payment_utils.generate_access_token(
            self.partner_id.id, self.amount, self.currency_id.id
        )

    @api.depends(
        'description', 'amount', 'currency_id', 'partner_id', 'company_id',
        'payment_provider_selection',
    )
    def _compute_link(self):
        for payment_link in self:
            related_document = self.env[payment_link.res_model].browse(payment_link.res_id)
            base_url = related_document.get_base_url()  # Don't generate links for the wrong website
            url_params = {
                'reference': payment_link.description,
                'amount': self.amount,
                'access_token': self._get_access_token(),
                **self._get_additional_link_values(),
            }
            if payment_link.payment_provider_selection != 'all':
                url_params['provider_id'] = str(payment_link.payment_provider_selection)
            payment_link.link = f'{base_url}/payment/pay?{urls.url_encode(url_params)}'

    def _get_additional_link_values(self):
        """ Return the additional values to append to the payment link.

        Note: self.ensure_one()

        :return: The additional payment link values.
        :rtype: dict
        """
        self.ensure_one()
        return {
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
        }
