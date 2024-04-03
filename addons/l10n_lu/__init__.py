# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID

from . import models

def _post_init_hook(cr, registry):
    _preserve_tag_on_taxes(cr, registry)
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_lu.lu_2011_chart_1').process_coa_translations()

def _preserve_tag_on_taxes(cr, registry):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(cr, registry, 'l10n_lu')
