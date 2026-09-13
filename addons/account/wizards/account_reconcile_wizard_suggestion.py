from odoo import _, api, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountReconcileWizard(models.TransientModel):
    _inherit = "account.reconcile.wizard"

    @api.depends("move_line_ids.move_id", "date")
    def _compute_lock_date_violated_warning_message(self):
        for wizard in self:
            date_after_lock = wizard._get_date_after_lock_date()
            lock_date_violated_warning_message = None
            if date_after_lock:
                lock_date_violated_warning_message = _(
                    "The date you set violates the lock date of one of your entry. It will be overriden by the following date : %(replacement_date)s",
                    replacement_date=date_after_lock,
                )
            wizard.lock_date_violated_warning_message = (
                lock_date_violated_warning_message
            )

    @api.depends("company_id", "move_line_ids.partner_id", "amount")
    @_debug.perf.timed
    def _compute_reco_model_autocomplete_ids(self):
        for wizard in self:
            domain = [
                ("company_id", "=", wizard.company_id.id),
                "|",
                ("match_partner_ids", "=", False),
                (
                    "match_partner_ids",
                    "any",
                    [("id", "in", wizard.move_line_ids.partner_id.ids)],
                ),
                "|",
                ("match_amount", "=", False),
                "|",
                "&",
                ("match_amount", "=", "lower"),
                ("match_amount_max", ">", wizard.amount),
                "|",
                "&",
                ("match_amount", "=", "greater"),
                ("match_amount_min", "<", wizard.amount),
                "&",
                ("match_amount", "=", "between"),
                "&",
                ("match_amount_min", "<", wizard.amount),
                ("match_amount_max", ">", wizard.amount),
                "|",
                ("match_journal_ids", "=", False),
                ("match_journal_ids", "in", wizard.move_line_ids.journal_id.ids),
                ("created_automatically", "=", False),
            ]
            query = self.env["account.reconcile.model"]._search(
                domain, bypass_access=True
            )
            reco_model_ids = [
                r[0]
                for r in self.env.execute_query(
                    SQL(
                        """
                SELECT account_reconcile_model.id
                FROM %s
                JOIN account_reconcile_model_line line ON line.model_id = account_reconcile_model.id
                WHERE %s
                GROUP BY account_reconcile_model.id
                HAVING COUNT(account_reconcile_model.id) = 1
            """,
                        query.from_clause,
                        query.where_clause or SQL("TRUE"),
                    )
                )
            ]
            _debug.pipeline(
                "reco_model_suggestions_found",
                recwizard=wizard,
                models=len(reco_model_ids),
            )
            wizard.reco_model_autocomplete_ids = self.env[
                "account.reconcile.model"
            ].browse(reco_model_ids)

    @api.onchange("reco_model_id")
    def _onchange_reco_model_id(self):
        model_line = self.reco_model_id.line_ids
        if len(model_line) != 1:
            return
        self.label = model_line.label
        self.tax_id = model_line.tax_ids[:1]
        self.account_id = model_line.account_id
