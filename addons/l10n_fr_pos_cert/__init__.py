# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models
from openerp import api, SUPERUSER_ID
from ..l10n_fr_certification.models.res_company import UNALTERABLE_COUNTRIES


def _setup_inalterability(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # enable ping for this module
    env['publisher_warranty.contract'].update_notification(cron_mode=True)

    fr_companies = env['res.company'].search([('partner_id.country_id.code', 'in', UNALTERABLE_COUNTRIES)])
    if fr_companies:
        # create the securisation sequence per company
        fr_companies._create_secure_sequence(['l10n_fr_pos_cert_sequence_id'])
