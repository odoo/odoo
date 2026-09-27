from unittest.mock import patch

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    with patch('odoo.addons.l10n_hu_edi.models.res_company.ResCompany._l10n_hu_edi_test_credentials', lambda self: None):
        for company in env['res.company'].search([('chart_template', '=', 'hu')], order="parent_path"):
            env['account.chart.template'].try_loading('hu', company)
