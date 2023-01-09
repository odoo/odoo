# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2022 Odoo S.A.
# @author -  Fekete Mihai <feketemihai@gmail.com>, Tatár Attila <atta@nvm.ro>
# Copyright (C) 2015 Tatár Attila
# Copyright (C) 2015 Forest and Biomass Services Romania (http://www.forbiom.eu).
# Copyright (C) 2011 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
# Copyright (C) 2009 (<http://www.filsystem.ro>)

from odoo import api, SUPERUSER_ID
from . import models


def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_ro.ro_chart_template').process_coa_translations()
