# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID


def _enrich_base_company(cr, registry):
    """ Will attempt to enrich the base company if sufficient information & credits are available.
    If the enrichment does not work, ignore the error as this is not a critical process. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.company._enrich()
