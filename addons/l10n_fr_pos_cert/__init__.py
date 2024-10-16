# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    AccountFiscalPosition, AccountSaleClosing, PosConfig, PosOrder, PosOrderLine,
    PosSession, ResCompany,
)
from .report import ReportL10n_Fr_Pos_CertReport_Pos_Hash_Integrity


def _setup_inalterability(env):
    # enable ping for this module
    env['publisher_warranty.contract'].update_notification(cron_mode=True)

    fr_companies = env['res.company'].search([('partner_id.country_id.code', 'in', env['res.company']._get_france_country_codes())])
    if fr_companies:
        fr_companies._create_secure_sequence(['l10n_fr_pos_cert_sequence_id'])
