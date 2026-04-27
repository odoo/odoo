# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountFinancialReportXMLReportExport(models.TransientModel):
    _inherit = "l10n_be_reports.periodic.vat.xml.export"

    def action_resume_post(self):
        """This action resumes the Post of an account move which was interrupted by this wizard"""
        options = self._l10n_be_reports_vat_export_generate_options()
        options['closing_entry'] = True

        move_ids = self.env['account.move'].browse(self.env.context['l10n_be_action_resume_post_move_ids'])
        return move_ids.with_context(l10n_be_reports_generation_options=options).action_post()
