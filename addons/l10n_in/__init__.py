# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import demo
from . import wizard

def init_settings(env):
    # Activate cash rounding by default for all companies as soon as the module is installed.
    group_user = env.ref('base.group_user').sudo()
    group_user._apply_group(env.ref('account.group_cash_rounding'))


def l10n_in_archive_tcs_tds_reports(env):
    """
    Archive old TCS & TDS reports on initial module installation (new DBs only).
    Existing DBs upgrading will skip post_init and preserve active old reports.
    """
    for xml_id in ('l10n_in.tcs_report', 'l10n_in.tds_report'):
        report = env.ref(xml_id, raise_if_not_found=False)
        if report:
            report.active = False


def post_init(env):
    init_settings(env)
    l10n_in_archive_tcs_tds_reports(env)
