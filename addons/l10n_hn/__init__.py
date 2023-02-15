# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009-2010 Salvatore J. Trimarchi <salvatore@trimarchi.co.cc>
# (http://salvatoreweb.co.cc)
from odoo import api, SUPERUSER_ID

def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_hn.cuentas_plantilla').process_coa_translations()
