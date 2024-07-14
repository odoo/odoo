# -*- coding: utf-8 -*-
from odoo import models


class AccountReportFileDownloadErrorWizard(models.TransientModel):
    _inherit = 'account.report.file.download.error.wizard'

    def saft_action_open_company(self, company_id):
        self.ensure_one()
        return self.env['account.general.ledger.report.handler'].action_fill_company_details({}, company_id)
