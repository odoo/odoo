# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, HttpCase
from odoo import tools


@tagged('-at_install', 'post_install', 'document_layout')
class TestAccountDocumentLayout(HttpCase):

    def test_render_account_document_layout(self):
        # YTI TODO: Adapt this tour without demo data
        if not tools.config["without_demo"]:
            report_layout = self.env.ref('web.report_layout_standard')
            main_company = self.env.ref('base.main_company')

            # Tour can't be run if the setup if not the generic one.
            generic_coa = self.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
            if not main_company.chart_template_id or main_company.chart_template_id != generic_coa:
                self.skipTest("Test render account document layout skipped: generic coa not found.")

            main_company.write({
                'primary_color': '#123456',
                'secondary_color': '#789101',
                'external_report_layout_id': report_layout.view_id.id,
            })
            self.env.ref('account.account_invoices_without_payment').write({
                'report_type': 'qweb-html',
            })
            self.start_tour("/web", 'account_render_report', login='admin', timeout=200)
