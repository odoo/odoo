# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_it_edi_register = fields.Boolean(
        compute='_compute_l10n_it_edi_register',
        inverse='_set_l10n_it_edi_mode',
        readonly=False)
    l10n_it_edi_mode = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test (experimental)'), ('prod', 'Official')],
        compute="_compute_l10n_it_edi_mode", inverse="_set_l10n_it_edi_mode", readonly=False)
    l10n_it_edi_mode_old = fields.Selection(related="company_id.l10n_it_edi_mode")

    @api.depends('company_id')
    def _compute_l10n_it_edi_register(self):
        for config in self:
            config.l10n_it_edi_register = bool(config.l10n_it_edi_mode_old)

    @api.depends('company_id')
    def _compute_l10n_it_edi_mode(self):
        for config in self:
            config.l10n_it_edi_mode = config.l10n_it_edi_mode_old

    @api.depends('company_id', 'l10n_it_edi_register')
    def _set_l10n_it_edi_mode(self):
        for config in self:
            # This is just for access tests, as it shouldn't be possible to set False back
            if not config.l10n_it_edi_mode:
                continue
            if not config.l10n_it_edi_register:
                raise ValidationError(_("Please explicitly allow Odoo to process your E-invoices."))
            config.button_create_proxy_user()

    def button_create_proxy_user(self):
        old_proxy_user = self.company_id.l10n_it_active_proxy_user_id
        if not old_proxy_user or old_proxy_user.edi_mode != self.l10n_it_edi_mode:
            fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
            edi_identification = fattura_pa._get_proxy_identification(self.company_id)
            if edi_identification:
                self.company_id.register_proxy_user(self.l10n_it_edi_mode)
