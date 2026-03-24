# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.safe_eval import safe_whitelist

from . import controllers
from . import models
from . import report
from . import wizard

safe_whitelist.add_function('odoo.addons.crm.tests.test_crm_lead_merge.TestLeadMerge.test_lead_merge_properties_formatting.<locals>.*')
