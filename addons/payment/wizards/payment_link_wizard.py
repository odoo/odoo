# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import ustr, consteq


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
                'description': record.invoice_payment_ref,
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
    link = fields.Char(string='Payment Link', compute='_compute_values')
    description = fields.Char('Payment Ref')
    access_token = fields.Char(compute='_compute_values')

    @api.onchange('amount', 'description')
    def _onchange_amount(self):
        if self.amount_max < self.amount:
            raise ValidationError(_("Please set an amount smaller than %s.") % (self.amount_max))
        if self.amount <= 0:
            raise ValidationError(_("The value of the payment amount must be positive."))

    @api.depends('amount', 'description', 'partner_id', 'currency_id')
    def _compute_values(self):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        for payment_link in self:
            token_str = '%s%s%s' % (payment_link.partner_id.id, payment_link.amount, payment_link.currency_id.id)
            payment_link.access_token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
        # must be called after token generation, obvsly - the link needs an up-to-date token
        self._generate_link()

    def _generate_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for payment_link in self:
            payment_link.link = '%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s&partner_id=%s&access_token=%s' % (base_url, payment_link.description, payment_link.amount, payment_link.currency_id.id, payment_link.partner_id.id, payment_link.access_token)

    @api.model
    def check_token(self, access_token, partner_id, amount, currency_id):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token_str = '%s%s%s' % (partner_id, amount, currency_id)
        correct_token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
        if consteq(ustr(access_token), correct_token):
            return True
        return False