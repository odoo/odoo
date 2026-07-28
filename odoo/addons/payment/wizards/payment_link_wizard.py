# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_repr

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
    link = fields.Char(string="Payment Link", compute='_compute_link')
    company_id = fields.Many2one('res.company', compute='_compute_company_id')
    warning_message = fields.Char(compute='_compute_warning_message')

    @api.depends('amount', 'amount_max')
    def _compute_warning_message(self):
        self.warning_message = ''
        for wizard in self:
            if wizard.amount_max <= 0:
                wizard.warning_message = _("There is nothing to be paid.")
            elif wizard.amount <= 0:
                wizard.warning_message = _("Please set a positive amount.")
            elif wizard.amount > wizard.amount_max:
                wizard.warning_message = _("Please set an amount lower than %s.", wizard.amount_max)

    @api.depends('res_model', 'res_id')
    def _compute_company_id(self):
        for link in self:
            record = self.env[link.res_model].browse(link.res_id)
            link.company_id = record.company_id if 'company_id' in record else False

    def _get_access_token(self):
        self.ensure_one()
        return payment_utils.generate_access_token(
            self.partner_id.id,
            float(float_repr(self.amount, self.currency_id.decimal_places)),
            self.currency_id.id,
        )

    @api.depends('amount', 'currency_id', 'partner_id', 'company_id')
    def _compute_link(self):
        for payment_link in self:
            related_document = self.env[payment_link.res_model].browse(payment_link.res_id)
            base_url = related_document.get_base_url()  # Don't generate links for the wrong website
            url_params = {
                'amount': float(float_repr(self.amount, self.currency_id.decimal_places)),
                'access_token': self._get_access_token(),
                **self._get_additional_link_values(),
            }
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
