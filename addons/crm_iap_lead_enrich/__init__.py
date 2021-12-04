# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo.api import Environment, SUPERUSER_ID


def _synchronize_cron(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {'active_test': False})
    cron = env.ref('crm_iap_lead_enrich.ir_cron_lead_enrichment')
    if cron:
        config = env['ir.config_parameter'].get_param('crm.iap.lead.enrich.setting', 'manual')
        cron.active = config != 'manual'
