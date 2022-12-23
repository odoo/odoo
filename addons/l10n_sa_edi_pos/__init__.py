# -*- coding: utf-8 -*-

from . import models
from odoo import api, SUPERUSER_ID


def _regenerate_company_journals_csr(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sa_journals = env['account.journal'].search([('country_code', '=', 'SA')])
    sa_journals._l10n_sa_compute_csr()

