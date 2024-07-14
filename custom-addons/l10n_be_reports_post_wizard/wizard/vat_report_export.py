# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountFinancialReportXMLReportExport(models.TransientModel):
    _inherit = "l10n_be_reports.periodic.vat.xml.export"

    def action_resume_post(self):
        """This action resumes the Post of an account move which was interrupted by this wizard"""
        options = {
            'closing_entry': True,
            'ask_restitution': self.ask_restitution,
            'ask_payment': self.ask_payment,
            'client_nihil': self.client_nihil,
            'comment': self.comment,
        }

        move_ids = self.env['account.move'].browse(self.env.context['l10n_be_action_resume_post_move_ids'])
        return move_ids.with_context(l10n_be_reports_generation_options=options).action_post()
