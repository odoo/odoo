# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_it_edi_already_registered = fields.Boolean(compute='_compute_l10n_it_edi_already_registered')
    l10n_it_edi_register_user = fields.Boolean(
        compute='_compute_l10n_it_edi_register_user',
        inverse='_set_l10n_it_edi_register_user',
        store=True)
    l10n_it_edi_operating_mode = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test (Experimental)'), ('prod', 'Official')],
        compute='_compute_l10n_it_edi_operating_mode',
        inverse='_set_l10n_it_edi_operating_mode',
        readonly=False)

    @api.depends('company_id')
    def _compute_l10n_it_edi_operating_mode(self):
        for config in self:
            proxy_user = config.company_id.l10n_it_edi_proxy_user
            config.l10n_it_edi_operating_mode = proxy_user and proxy_user.edi_operating_mode or 'demo'

    @api.depends('l10n_it_edi_operating_mode')
    def _set_l10n_it_edi_operating_mode(self, *args):
        if not self.l10n_it_edi_register_user:
            company = self.company_id
            raise UserError(_("Please authorize Odoo to handle your invoices by checking the field below for the company %s (id=%s)", company.name, company.id))
        self.company_id._set_l10n_it_edi_proxy_user(self.l10n_it_edi_operating_mode)

    @api.depends('company_id')
    def _compute_l10n_it_edi_register_user(self):
        """ This field will be changed by the user """
        for config in self:
            config.l10n_it_edi_register_user = bool(config.company_id._get_proxy_users('fattura_pa'))

    @api.depends('company_id')
    def _compute_l10n_it_edi_already_registered(self):
        """ This field will hold the old value while the user changes l10n_it_edi_register_user
            Needed to compute the 'invisible' attribute in the view.
        """
        for config in self:
            config.l10n_it_edi_already_registered = bool(config.company_id._get_proxy_users('fattura_pa'))

    def _set_l10n_it_edi_register_user(self):
        """ If l10n_it_edi_operating_mode is on, let _l10n_it_edi_set_proxy_user create the user """
        for config in self:
            if not config.l10n_it_edi_operating_mode and not self.company_id.l10n_it_edi_proxy_user:
                config.l10n_it_edi_operating_mode = 'demo'
