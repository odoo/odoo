# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.onchange('lead_enrich_auto')
    def _onchange_cron_lead_enrich(self):
        """ change the active status of the cron according to the settings"""
        if self.module_crm_iap_lead_enrich == True:
            cron = self.sudo().with_context(active_test=False).env.ref('crm_iap_lead_enrich.ir_cron_lead_enrichment')
            if cron:
                cron.active = self.lead_enrich_auto != 'manual'
