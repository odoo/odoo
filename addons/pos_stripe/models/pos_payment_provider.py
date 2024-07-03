from odoo import fields, models, _


class PosPaymentProvider(models.Model):
    _inherit = 'pos.payment.provider'

    code = fields.Selection(selection_add=[('stripe', 'Stripe')], ondelete={'stripe': 'set default'})
    is_stripe_provider_configured = fields.Boolean(compute="_compute_is_stripe_provider_configured")

    def _compute_is_stripe_provider_configured(self):
        provider_id = self.env['payment.provider'].search([('code', '=', 'stripe'), ('company_id', '=', self.env.company.id), ('stripe_secret_key', '!=', False)], limit=1).id
        for record in self:
            if provider_id:
                record.is_stripe_provider_configured = True
            else:
                record.is_stripe_provider_configured = False

    def action_stripe_key(self):
        res_id = self.env['payment.provider'].search([('code', '=', 'stripe'), ('company_id', '=', self.env.company.id)], limit=1).id
        # Redirect
        return {
            'name': _('Stripe'),
            'res_model': 'payment.provider',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': res_id,
        }
