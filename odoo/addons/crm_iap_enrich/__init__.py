# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _synchronize_cron(env):
    cron = env.ref('crm_iap_enrich.ir_cron_lead_enrichment')
    if cron:
        config = env['ir.config_parameter'].get_param('crm.iap.lead.enrich.setting', 'auto')
        cron.active = config == 'auto'
