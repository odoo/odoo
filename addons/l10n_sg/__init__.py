# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2014 Tech Receptives (<http://techreceptives.com>).
from . import models


def _l10n_sg_post_init(env):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(env, 'l10n_sg')
    if registering_cron := env.ref('account_peppol.ir_cron_peppol_auto_register_services', raise_if_not_found=False):
        registering_cron._trigger()


def _l10n_sg_uninstall(env):
    env['account_edi_proxy_client.user']._peppol_auto_deregister_services('l10n_sg')
