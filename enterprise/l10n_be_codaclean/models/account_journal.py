import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, modules
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import exception_to_unicode

from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.l10n_be_codaclean.tools.iap_api import get_error_message

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def __get_bank_statements_available_sources(self):
        # Extends 'account'
        rslt = super().__get_bank_statements_available_sources()
        rslt.append(("l10n_be_codaclean", _("Codaclean Synchronization")))
        return rslt

    @api.model
    def _l10n_be_codaclean_fetch_coda_transactions(self, company):
        if not company.l10n_be_codaclean_is_connected:
            raise RedirectWarning(
                message=_("Not connected to Codaclean. Please check your configuration."),
                action=self.env.ref('account.action_account_config').id,
                button_text=_("Go to settings"),
            )

        codaclean_journals = self.search([
            ("bank_statements_source", "=", "l10n_be_codaclean"),
            ("bank_acc_number", "!=", False),
            ("company_id", "=", company.id),
        ])
        if not codaclean_journals:
            return []

        # We fetch only coda files with a statment date after
        # - The most recent bank statement
        # - The most recent bank statement line (if there are no bank statements)
        # - The date 1 year ago (if we did not find bank statement lines either)
        last_statement_date = dict(self.env["account.bank.statement"]._read_group(
            domain=[('journal_id', 'in', codaclean_journals.ids)],
            groupby=['journal_id'],
            aggregates=['date:max'],
        ))
        # Note that there can be entries with value `False` in last_statement_date
        remaining_journals = self.browse([journal.id for journal in codaclean_journals if not last_statement_date.get(journal)])
        last_statement_line_date = dict(self.env["account.bank.statement.line"]._read_group(
            domain=[('journal_id', 'in', remaining_journals.ids)],
            groupby=['journal_id'],
            aggregates=['date:max'],
        )) if remaining_journals else {}
        date_one_year_ago = fields.Date.today() - relativedelta(years=1)

        ibans = {}  # {iban: last_date} where last_date is the date of the last bank statement or transaction
        for journal in codaclean_journals:
            iban = journal.bank_acc_number.replace(" ", "").upper()
            # Note that there can be entries with value `False` in last_statement_date / last_statement_line_date
            last_date = last_statement_date.get(journal) or last_statement_line_date.get(journal) or date_one_year_ago
            ibans[iban] = min(ibans.get(iban) or last_date, last_date)
        date_from = min(ibans.values()) or date_one_year_ago

        # Format the dates
        ibans = {iban: fields.Date.to_string(date) for iban, date in ibans.items()}
        date_from = fields.Date.to_string(date_from)

        result = company._l10n_be_codaclean_fetch_coda_files(date_from, ibans)
        if not company.l10n_be_codaclean_iap_token:
            # Modify the status in a new cursor to prevent the changes from being rolled back
            with company.pool.cursor() as new_cr:
                company = company.with_env(company.env(cr=new_cr))
                company.l10n_be_codaclean_iap_token = False
        if error := result.get("error", {}):
            raise UserError(get_error_message(error))

        return result.get('files', [])

    @api.model
    def _l10n_be_codaclean_import_coda_files(self, company, codas):
        if not codas:
            return []

        statement_ids_all = []
        skipped_bank_accounts = set()
        # A same account number could be formatted differently in journal.acc_number and
        # coda statement. Therefor we must match sanitized versions of both.
        # (A _read_group with `groupby=['bank_acc_number']` throws a `ValueError` so we use `grouped`.)
        acc_journal_map = self.search([
            ("company_id", "=", company.id),
            ("bank_statements_source", "in", ("l10n_be_codaclean", "undefined")),
            ("bank_acc_number", "!=", False),
        ]).grouped(lambda journal: sanitize_account_number(journal.bank_acc_number))
        for coda_b64, pdf_b64 in codas:
            try:
                coda_attachment = self.env["ir.attachment"].create({
                    "name": 'codaclean_coda.coda',
                    'type': 'binary',
                    'datas': coda_b64,
                })
                currency, account_number, stmt_vals = self._parse_bank_statement_file(coda_attachment)
                journal = next((
                    journal
                    for journal in acc_journal_map.get(sanitize_account_number(account_number), [])
                    if journal.currency_id.name or journal.company_id.currency_id.name == currency
                ), False)
                if journal:
                    journal.bank_statements_source = "l10n_be_codaclean"
                else:
                    skipped_bank_accounts.add(f"{account_number} ({currency})")
                    continue
                stmt_vals = journal._complete_bank_statement_vals(stmt_vals, journal, account_number, coda_attachment)
                statement_ids, __, __ = journal.with_context(skip_pdf_attachment_generation=True)._create_bank_statements(stmt_vals, raise_no_imported_file=False)
                if statement_ids:
                    statement_ids_all.extend(statement_ids)
                    # We can not add an attachment to multiple bank statements at once.
                    # (See function `write` of model 'account.bank.statement' in module 'account'.)
                    pdf_attachment = self.env['ir.attachment'].create({
                        'name': 'codaclean_pdf.pdf',
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                        'datas': pdf_b64,
                    })
                    for statement in self.env['account.bank.statement'].browse(statement_ids):
                        statement.attachment_ids |= pdf_attachment
                    # We may have a lot of statements to import, so we commit after each so that a later error doesn't discard previous work
                    if not modules.module.current_test:
                        self.env.cr.commit()
            except (UserError, ValueError) as e:
                _logger.error("Error while importing Codaclean file: %s", e)
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                self.env.cr.rollback()
        if skipped_bank_accounts:
            _logger.info("No journals were found for the following bank accounts parsed from the Coda files: %s", ','.join(skipped_bank_accounts))
        return statement_ids_all

    def l10n_be_codaclean_manually_fetch_coda_transactions(self):
        self.ensure_one()
        codas = self._l10n_be_codaclean_fetch_coda_transactions(self.company_id)
        statement_ids = self._l10n_be_codaclean_import_coda_files(self.company_id, codas)
        return self.env["account.bank.statement.line"]._action_open_bank_reconciliation_widget(
            extra_domain=[("statement_id", "in", statement_ids)],
        )

    @api.model
    def _l10n_be_codaclean_cron_fetch_coda_transactions(self):
        coda_companies = self.env['res.company'].search([
            ('l10n_be_codaclean_is_connected', '=', True),
        ])
        if not coda_companies:
            _logger.info("No company is connected to Codaclean.")
            return
        for company in coda_companies:
            # We want to avoid raising in the cron
            try:
                codas = self._l10n_be_codaclean_fetch_coda_transactions(company)
            except (UserError, RedirectWarning) as e:
                _logger.warning("Fetching coda files for company '%s' (id = %s) failed: %s", company.name, company.id, exception_to_unicode(e))
                continue
            _logger.info("%s coda files were fetched for company '%s' (id = %s).", len(codas), company.name, company.id)
            statement_count = len(self._l10n_be_codaclean_import_coda_files(company, codas))
            _logger.info("%s bank statements were imported for company '%s' (id = %s).", statement_count, company.name, company.id)
