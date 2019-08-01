# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This module is Copyright (c) 2009-2013 General Solutions (http://gscom.vn) All Rights Reserved.

from . import models
from odoo import api, SUPERUSER_ID

def _preserve_tag_on_taxes(cr, registry):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(cr, registry, 'l10n_vn')

def load_translations(env):
    env.ref('l10n_vn.vn_template').process_coa_translations()

def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    load_translations(env)
    _preserve_tag_on_taxes(cr, registry)
