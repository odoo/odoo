# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PaymentLinkWizard(models.TransientModel):
    _name = "payment.link.wizard"
    _description = "Generate Payment Link"

    @api.model
    def default_get(self, fields):
        res = super(PaymentLinkWizard, self).default_get(fields)
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')
        res.update({'res_id': res_id, 'res_model': res_model})
        if res_id and res_model == 'account.invoice':
            record = self.env[res_model].browse(res_id)
            res.update({
                'description': record.reference,
                'amount': record.amount_total,
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'amount_max': record.amount_total
            })
        return res

    res_model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    amount_max = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')
    link = fields.Char(string='Payment Link')
    description = fields.Char('Payment Ref')

    @api.onchange('amount', 'description')
    def _onchange_amount(self):
        if self.amount_max < self.amount:
            raise ValidationError(_("Please set an amount smaller than %s.") % (self.amount_max))
        if self.amount <= 0:
            raise ValidationError(_("The value of the payment amount must be positive."))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.link = '%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s&partner_id=%s' % (base_url, self.description, self.amount, self.currency_id.id, self.partner_id.id)
