# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleQuoteTemplate(models.Model):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"

    def _get_default_require_signature(self):
        # A confirmation mode (sign or pay) is mandatory on a quotation template
        # If none has been activated in the settings, we force 'sign' as confirmation mode
        if not self.env.user.company_id.portal_confirmation_pay:
            return True
        return self.env.user.company_id.portal_confirmation_sign

    def _get_default_require_payment(self):
        return self.env.user.company_id.portal_confirmation_pay

    name = fields.Char('Quotation Template', required=True)
    quote_line = fields.One2many('sale.quote.line', 'quote_id', 'Quotation Template Lines', copy=True)
    note = fields.Text('Terms and conditions')
    options = fields.One2many('sale.quote.option', 'template_id', 'Optional Products Lines', copy=True)
    number_of_days = fields.Integer('Quotation Duration',
        help='Number of days for the validity date computation of the quotation')
    require_signature = fields.Boolean('Digital Signature', default=_get_default_require_signature, help='Request a digital signature to the customer in order to confirm orders automatically.')
    require_payment = fields.Boolean('Electronic Payment', default=_get_default_require_payment,help='Request an electronic payment to the customer in order to confirm orders automatically.')
    mail_template_id = fields.Many2one(
        'mail.template', 'Confirmation Mail',
        domain=[('model', '=', 'sale.order')],
        help="This e-mail template will be sent on confirmation. Leave empty to send nothing.")
    active = fields.Boolean(default=True, help="If unchecked, it will allow you to hide the quotation template without removing it.")

    @api.constrains('require_signature', 'require_payment')
    def _check_confirmation(self):
        for template in self:
            if not template.require_signature and not template.require_payment:
                raise ValidationError(_('Please select a confirmation mode in Confirmation: Digital Signature, Electronic Payment or both.'))

    @api.multi
    def open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/template/%d' % self.id
        }
