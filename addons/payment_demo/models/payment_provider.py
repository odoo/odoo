# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('demo', 'Demo')], ondelete={'demo': 'set default'})

    #=== COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'demo').show_credentials_page = False

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'demo').update({
            'support_fees': True,
            'support_manual_capture': True,
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    # === CONSTRAINT METHODS ===#

    @api.constrains('state', 'code')
    def _check_provider_state(self):
        if self.filtered(lambda p: p.code == 'demo' and p.state not in ('test', 'disabled')):
            raise UserError(_("Demo providers should never be enabled."))
