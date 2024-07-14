# -*- coding: utf-8 -*-
import logging

from odoo import models, _
from odoo.addons.l10n_be_codabox.const import raise_deprecated

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def __get_bank_statements_available_sources(self):
        rslt = super().__get_bank_statements_available_sources()
        rslt.append(("l10n_be_codabox", _("CodaBox Synchronization")))
        return rslt

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        for journal_id in dashboard_data:
            journal = self.browse(journal_id)
            dashboard_data[journal_id]["l10n_be_codabox_is_connected"] = journal.company_id.l10n_be_codabox_is_connected
            dashboard_data[journal_id]["l10n_be_codabox_journal_is_soda"] = journal == journal.company_id.l10n_be_codabox_soda_journal

    def l10n_be_codabox_action_open_settings(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.config.settings",
            "view_mode": "form",
            "target": "self",
        }

    def l10n_be_codabox_manually_fetch_coda_transactions(self):
        self.ensure_one()
        statement_ids = self._l10n_be_codabox_fetch_coda_transactions(self.company_id)
        return self.env["account.bank.statement.line"]._action_open_bank_reconciliation_widget(
            extra_domain=[("statement_id", "in", statement_ids)],
        )

    def _l10n_be_codabox_cron_fetch_coda_transactions(self):
        coda_companies = self.env['res.company'].search([
            ('l10n_be_codabox_is_connected', '=', True),
        ])
        if not coda_companies:
            _logger.info("L10BeCodabox: No company is connected to Codabox.")
            return
        imported_statements = sum(len(self._l10n_be_codabox_fetch_coda_transactions(company)) for company in coda_companies)
        _logger.info("L10BeCodabox: %s bank statements were imported.", imported_statements)

    def _l10n_be_codabox_fetch_transactions_from_iap(self, session, company, file_type, date_from=None):
        raise_deprecated(self.env)

    def _l10n_be_codabox_fetch_coda_transactions(self, company):
        raise_deprecated(self.env)

    def l10n_be_codabox_manually_fetch_soda_transactions(self):
        raise_deprecated(self.env)
