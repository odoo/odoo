from odoo import fields, models
from odoo.tools.misc import format_date


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()

        pdp_journals = self.filtered(
            lambda j: (
                j.type == "sale"
                and j.code == "EREP"
                and j.company_id.country_code == "FR"
                and j.company_id.l10n_fr_pdp_enabled
            ),
        )
        if not pdp_journals:
            return dashboard_data

        Flow = self.env["l10n.fr.pdp.flow"]
        Move = self.env["account.move"]
        today = fields.Date.context_today(self)

        for journal in pdp_journals:
            company = journal.company_id
            data = dashboard_data[journal.id]
            data["pdp_is_ereporting_journal"] = True

            # ---------- Next due dates ----------
            def _get_due(report_kind):
                flow = Flow.search(
                    [
                        ("company_id", "=", company.id),
                        ("report_kind", "=", report_kind),
                        ("state", "in", ("draft", "building", "ready", "error")),
                        ("next_deadline_end", "!=", False),
                    ],
                    limit=1,
                    order="next_deadline_end asc",
                )
                if not flow:
                    return None, None
                due = flow.next_deadline_end
                return due, format_date(self.env, due)

            tx_due_raw, tx_due_str = _get_due("transaction")
            pay_due_raw, pay_due_str = _get_due("payment")

            data["pdp_tx_due"] = tx_due_str or False
            data["pdp_pay_due"] = pay_due_str or False

            # ---------- Errors ----------
            error_domain = [
                ("company_id", "=", company.id),
                ("l10n_fr_pdp_status", "=", "error"),
            ]
            error_count = Move.search_count(error_domain)
            data["pdp_error_count"] = error_count

            has_warning = bool(error_count)
            has_danger = False
            if error_count:
                deadlines = [d for d in (tx_due_raw, pay_due_raw) if d]
                if deadlines:
                    min_deadline = min(deadlines)
                    if (min_deadline - today).days <= 3:
                        has_danger = True

            data["pdp_has_warning"] = has_warning
            data["pdp_has_danger"] = has_danger

        return dashboard_data
