# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_edi_proxy_active = fields.Boolean(compute='_compute_is_edi_proxy_active')

    @api.depends('company_id.account_edi_proxy_client_ids', 'company_id.account_edi_proxy_client_ids.active')
    def _compute_is_edi_proxy_active(self):
        for config in self:
            config.is_edi_proxy_active = config.company_id.account_edi_proxy_client_ids

    def button_create_proxy_user(self):
        # For now, only fattura_pa uses the proxy.
        # To use it for more, we have to either make the activation of the proxy on a format basis
        # or create a user per format here (but also when installing new formats)
        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        edi_identification = fattura_pa._get_proxy_identification(self.company_id)
        if not edi_identification:
            return

        self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, fattura_pa, edi_identification)
