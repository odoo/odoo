import logging
import requests
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import models, _, fields
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg, get_iap_endpoint

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    ############################
    # COMMON CODABOX METHODS
    ############################

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        for journal_id in dashboard_data:
            journal = self.browse(journal_id)
            dashboard_data[journal_id]["l10n_be_codabox_is_connected"] = journal.company_id.l10n_be_codabox_is_connected
            dashboard_data[journal_id]["l10n_be_codabox_journal_is_soda"] = journal == journal.company_id.l10n_be_codabox_soda_journal
            if journal == journal.company_id.l10n_be_codabox_soda_journal:
                dashboard_data[journal_id]["l10n_be_codabox_number_draft"] = self.env['account.move'].search_count([
                    ('journal_id', '=', journal.id),
                    ('state', '=', 'draft'),
                ])

    def l10n_be_codabox_action_open_settings_open_draft_soda_entries(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("journal_id", "=", self.id), ("state", "=", "draft")],
            "target": "current",
        }

    def _l10n_be_codabox_fetch_transactions_from_iap(self, session, company, file_type, date_from=None, ibans=None):
        assert file_type in ("codas", "sodas")
        company._l10n_be_codabox_verify_prerequisites()
        if not date_from:
            date_from = fields.Date.to_string(fields.Date.today() - relativedelta(years=1))
        params = {
            "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "fidu_vat": company.l10n_be_codabox_fiduciary_vat,
            "company_vat": company.l10n_be_codabox_company_vat,
            "iap_token": company.sudo().l10n_be_codabox_iap_token,
            "from_date": date_from,
        }
        if file_type == "sodas":
            method = "get_soda_files"
        else:
            method = "get_coda_files"
            params["ibans"] = ibans
        try:
            response = session.post(f"{get_iap_endpoint(self.env)}/{method}", json={"params": params}, timeout=(10, 900))
            result = response.json().get("result", {})
            error = result.get("error")
            if error:
                if error.get("type") in ("error_connection_not_found", "error_consent_not_valid"):
                    # Modify the status in a new cursor to avoid the current transaction to be rolled back
                    with self.pool.cursor() as new_cr:
                        company = company.with_env(self.env(cr=new_cr))
                        company.l10n_be_codabox_is_connected = False
                if not self.env.context.get("l10n_be_codabox_from_cron"):  # avoid disabling cron if too many fails
                    raise UserError(get_error_msg(error))
                else:
                    _logger.error("L10nBeCodabox: CRON %s error: %s", file_type, error)
            return result.get("files", [])
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if not self.env.context.get("l10n_be_codabox_from_cron"):
                raise UserError(get_error_msg({"type": "error_connecting_iap"}))
            else:
                _logger.error("L10nBeCodabox: CRON %s error: error_connecting_iap", file_type)
        return []

    ############################
    # CODA METHODS
    ############################

    def __get_bank_statements_available_sources(self):
        rslt = super().__get_bank_statements_available_sources()
        rslt.append(("l10n_be_codabox", _("CodaBox Synchronization")))
        return rslt

    def _l10n_be_codabox_fetch_coda_transactions(self, company):
        if not company.l10n_be_codabox_is_connected:
            raise UserError(get_error_msg({"type": "error_codabox_not_configured"}))

        date_one_year_ago = fields.Date.to_string(fields.Date.today() - relativedelta(years=1))
        ibans = {}  # {iban: last_date} where last_date is the date of the last bank statement or transaction
        codabox_journals = self.search([
            ("bank_statements_source", "=", "l10n_be_codabox"),
            ("bank_acc_number", "!=", False),
            ("company_id", "=", company.id),
        ])
        for journal in codabox_journals:
            last_date = self.env["account.bank.statement"].search([
                ("journal_id", "=", journal.id),
            ], order="date DESC", limit=1).date
            if not last_date:
                last_date = self.env["account.bank.statement.line"].search([
                    ("journal_id", "=", journal.id),
                ], order="date DESC", limit=1).date
            iban = journal.bank_acc_number.replace(" ", "").upper()
            last_date = fields.Date.to_string(last_date) or date_one_year_ago
            if iban not in ibans:
                ibans[iban] = last_date
            else:
                ibans[iban] = min(ibans[iban], last_date)
        lock_date = max(company.user_fiscalyear_lock_date, company.user_hard_lock_date)
        date_from = max(min(ibans.values()) if ibans else date_one_year_ago, fields.Date.to_string(lock_date))
        statement_ids_all = []
        skipped_bank_accounts = set()
        session = requests.Session()
        codas = self._l10n_be_codabox_fetch_transactions_from_iap(session, company, "codas", date_from, ibans)

        journal_stats = defaultdict(lambda: {
            "count": 0,
            "dates": [],
            "currency": None,
        })
        imported_files = 0
        for coda in codas:
            try:
                coda_raw_b64, coda_pdf_b64 = coda
                coda_attachment = self.env["ir.attachment"].create({
                    "name": _("Original CodaBox.coda"),
                    'type': 'binary',
                    'datas': coda_raw_b64,
                })
                # We parse first the CODA to get the IBAN and Currency so that we can select a matching journal
                currency, account_number, __ = self.with_context(ignore_statements=True)._parse_bank_statement_file(coda_attachment)
                journal = self.search([
                    ("bank_acc_number", "=", account_number),
                    ("bank_statements_source", "in", ("l10n_be_codabox", "undefined")),
                    "|",
                        ("currency_id.name", "=", currency),
                        "&",
                            ("currency_id", "=", False),
                            ("company_id.currency_id.name", "=", currency),
                ], limit=1)
                if journal:
                    journal.bank_statements_source = "l10n_be_codabox"
                else:
                    skipped_bank_accounts.add(f"{account_number} ({currency})")
                    continue
                # We reparse now to have all info including the statements
                currency, account_number, stmt_vals = journal._parse_bank_statement_file(coda_attachment)
                stmt_vals = journal._complete_bank_statement_vals(stmt_vals, journal, account_number, coda_attachment)
                statement_id, __, __ = journal.with_context(skip_pdf_attachment_generation=True)._create_bank_statements(stmt_vals, raise_no_imported_file=False)
                if statement_id:
                    # Logging part
                    imported_files += 1
                    stats = journal_stats[journal]
                    stats['count'] += 1
                    stats['currency'] = currency
                    stats['dates'].append(stmt_vals[0].get('date'))

                    statement_ids_all.extend(statement_id)
                    pdf = self.env['ir.attachment'].create({
                        'name': _("Original CodaBox Bank Statement.pdf"),
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                        'datas': coda_pdf_b64,
                        'res_model': 'account.bank.statement',
                        'res_id': statement_id[0],
                    })
                    self.env['account.bank.statement'].browse(statement_id).attachment_ids |= pdf + coda_attachment
                    # We may have a lot of files to import, so we commit after each file so that a later error doesn't discard previous work
                    self.env.cr.commit()
            except (UserError, ValueError) as e:
                _logger.error("L10nBeCodabox: Error while importing CodaBox file: %s", e)
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                self.env.cr.rollback()

        _logger.info("L10nBeCodabox: Coda import summary - Fetched: %s - Imported: %s - Journals: %s", len(codas), imported_files, len(journal_stats))
        for journal, stats in journal_stats.items():
            _logger.info("%s (%s): %s transactions (From: %s - To: %s) with currency %s", journal.code, journal.id, stats['count'], min(stats['dates']), max(stats['dates']), stats["currency"])

        if skipped_bank_accounts:
            _logger.info("L10nBeCodabox: No journals were found for the following bank accounts found in CodaBox: %s", ','.join(skipped_bank_accounts))
        return statement_ids_all

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
            _logger.info("L10BeCodabox: CODA No company is connected to CodaBox.")
            return
        for company in coda_companies:
            self.with_context(l10n_be_codabox_from_cron=True)._l10n_be_codabox_fetch_coda_transactions(company)

    ############################
    # SODA METHODS
    ############################

    def _l10n_be_codabox_fetch_soda_transactions(self, company):
        soda_journal = company.l10n_be_codabox_soda_journal
        session = requests.Session()
        last_soda_date = self.env["account.move"].search([
            ("journal_id", "=", soda_journal.id),
        ], order="date DESC", limit=1).date
        if not last_soda_date:
            last_soda_date = fields.Date.today() - relativedelta(years=2)  # API goes back 2 years max

        lock_date = max(company.user_fiscalyear_lock_date, company.user_hard_lock_date)
        date_from = max(last_soda_date, lock_date)
        sodas = self._l10n_be_codabox_fetch_transactions_from_iap(session, soda_journal.company_id, "sodas", fields.Date.to_string(date_from))
        _logger.info("L10nBeCodabox: %s SODAs fetched", len(sodas))
        moves = self.env["account.move"]
        for soda in sodas:
            try:
                soda_raw_b64, soda_pdf_b64 = soda
                attachment_soda = self.env["ir.attachment"].create({
                    "name": _("Original CodaBox SODA.xml"),
                    'type': 'binary',
                    'datas': soda_raw_b64,
                    'company_id': self.company_id.id,
                })
                move = soda_journal.with_context(raise_no_imported_file=False)._l10n_be_parse_soda_file(attachment_soda, skip_wizard=True)
                if move:
                    attachment_pdf = self.env["ir.attachment"].create({
                        'name': _("Original CodaBox Payroll Statement.pdf"),
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                        'datas': soda_pdf_b64,
                        'res_model': move._name,
                        'res_id': move.id,
                    })
                    move.attachment_ids += attachment_pdf + attachment_soda
                    moves += move
                    # We may have a lot of files to import, so we commit after each file so that a later error doesn't discard previous work
                    self.env.cr.commit()
            except (UserError, ValueError) as e:
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                _logger.error("L10nBeCodabox: Error while importing CodaBox file: %s", e)
                self.env.cr.rollback()
        return moves

    def l10n_be_codabox_manually_fetch_soda_transactions(self):
        self.ensure_one()
        moves = self._l10n_be_codabox_fetch_soda_transactions(self.company_id)
        if not moves:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No SODA imported"),
                    "message": _("No new SODA is available for import."),
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", moves.ids)],
        }

    def _l10n_be_codabox_cron_fetch_soda_transactions(self):
        codabox_companies = self.env['res.company'].search([
            ('l10n_be_codabox_is_connected', '=', True),
            ('l10n_be_codabox_soda_journal', '!=', False),
        ])
        if not codabox_companies:
            _logger.info("L10BeCodabox: SODA No company is connected to CodaBox.")
            return
        for company in codabox_companies:
            imported_moves = self.with_context(l10n_be_codabox_from_cron=True)._l10n_be_codabox_fetch_soda_transactions(company)
            _logger.info("L10BeCodabox: %s payroll statements were imported.", len(imported_moves))
