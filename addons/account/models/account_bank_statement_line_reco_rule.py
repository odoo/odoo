import re
from collections import defaultdict

from odoo import SUPERUSER_ID, Command, _, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_is_zero

from odoo.addons.account.tools.structured_reference import is_valid_structured_reference

_debug = DebugLog(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @_debug.perf.timed
    def _action_manual_reco_model(self, reco_model_id):
        _debug.lifecycle("_action_manual_reco_model", records=self)
        self.move_id.line_ids.filtered(
            lambda x: x.account_id == x.move_id.journal_id.suspense_account_id
        ).reconcile_model_id = reco_model_id

    @_debug.perf.timed
    def _create_automatic_reconciliation_model(self, account_move_line, account):
        self._handle_reconciliation_rule(account_move_line, account.id)
        new_rule = self._check_and_create_reconciliation_rule(
            account.id, self.company_id.id
        )

        if new_rule:
            return self.env["account.bank.statement.line"].search(
                [
                    ("journal_id", "=", self.journal_id.id),
                    ("is_reconciled", "=", False),
                    ("move_id.line_ids.reconcile_model_id", "=", new_rule.id),
                ]
            )

        self._post_matching_done_confirmation()
        return self.env["account.bank.statement.line"]

    def _handle_reconciliation_rule(self, aml, account_id):
        should_delete_rule = (
            aml.reconcile_model_id.created_automatically
            and account_id not in aml.reconcile_model_id.line_ids.account_id.ids
        )
        if should_delete_rule:
            _debug.logic(
                "auto_rule_no_longer_matches",
                stline=self,
                reconcile_model_id=aml.reconcile_model_id,
                account_id=account_id,
            )
            aml.reconcile_model_id.sudo().unlink()

    @_debug.perf.timed
    def _check_and_create_reconciliation_rule(self, account_id, company_id):
        bank_stmt_line_domain = [
            ("company_id", "=", company_id),
            ("journal_id", "=", self.journal_id.id),
            ("payment_ref", "!=", False),
            ("move_id.line_ids.account_id", "=", account_id),
            ("move_id.line_ids.reconcile_model_id", "=", False),
        ]
        previous_statement_lines = self.env["account.bank.statement.line"].search(
            bank_stmt_line_domain, limit=5, order="internal_index desc"
        )
        if len(previous_statement_lines) <= 1:
            _debug.logic(
                "no_auto_rule_line_account",
                stline=self,
                previous_statement_lines_count=len(previous_statement_lines),
                account_id=account_id,
            )
            return None

        existing_reco_models = self.env["account.reconcile.model"].search(
            [
                ("company_id", "=", company_id),
                ("line_ids.account_id", "=", account_id),
                ("match_journal_ids", "=", self.journal_id.ids),
                ("match_label", "=", "match_regex"),
                ("match_label_param", "!=", False),
            ]
        )
        for reco_model in existing_reco_models:
            pattern = re.compile(reco_model.match_label_param, re.IGNORECASE)
            previous_statement_lines = previous_statement_lines.filtered(
                lambda sl, pattern=pattern: (
                    sl.payment_ref and not pattern.search(sl.payment_ref)
                )
            )
            if len(previous_statement_lines) <= 1:
                return None

        rule_data = self._prepare_reconciliation_rule_data(
            previous_statement_lines, account_id
        )
        _debug.logic(
            "auto_rule_candidate",
            stline=self,
            substring=rule_data.get("common_substring"),
            partners=rule_data.get("partner_ids"),
        )
        if rule_data.get("common_substring"):
            return self._create_reconciliation_rule(rule_data)
        return None

    @_debug.perf.timed
    def _prepare_reconciliation_rule_data(self, statement_lines, account_id):
        payment_refs = [line.payment_ref.strip() for line in statement_lines]
        common_substring = self._get_common_substring(payment_refs)
        if not common_substring:
            return {}
        account = self.env["account.account"].browse(account_id)

        return {
            "name": account.name,
            "common_substring": common_substring,
            "account": account,
            "partner_ids": statement_lines.partner_id.ids
            if len(statement_lines.partner_id.ids) == 1
            else [],
        }

    @_debug.perf.timed
    def _create_reconciliation_rule(self, rule_data):
        vals = {
            "created_automatically": True,
            "name": rule_data["name"],
            "match_journal_ids": self.journal_id.ids,
            "match_label": "match_regex",
            "match_label_param": rule_data["common_substring"],
            "line_ids": [
                Command.create(
                    {
                        "account_id": rule_data["account"].id,
                        "amount_type": "percentage",
                        "amount_string": "100",
                    }
                ),
            ],
        }

        if rule_data["partner_ids"]:
            vals["match_partner_ids"] = rule_data["partner_ids"]

        return (
            self.with_user(SUPERUSER_ID)
            .with_company(self.journal_id.company_id)
            .env["account.reconcile.model"]
            .create(vals)
        )

    @_debug.perf.timed
    def _get_common_substring(self, labels):
        def normalise_label(label):
            is_valid = is_valid_structured_reference(label)
            label = re.escape(label)
            if not is_valid:
                label = re.sub(r"\d+", r"\\d+", label)
            return label

        def common_substrings(label, olabel):
            olabel_substring_positions = defaultdict(list)
            for idx in range(len(olabel) - 9):
                olabel_substring_positions[olabel[idx : idx + 10]].append(idx + 9)
            for label_starting_pos in range(len(label) - 9):
                for olabel_end_pos in olabel_substring_positions[
                    label[label_starting_pos : label_starting_pos + 10]
                ]:
                    label_end_pos = label_starting_pos + 9
                    current_substring = label[label_starting_pos:label_end_pos]
                    while (
                        label_end_pos < len(label)
                        and olabel_end_pos < len(olabel)
                        and label[label_end_pos] == olabel[olabel_end_pos]
                    ):
                        current_substring += label[label_end_pos]
                        label_end_pos += 1
                        olabel_end_pos += 1
                        if current_substring[-1] != "\\":
                            yield current_substring

        normalised = [normalise_label(label.upper()) for label in labels if label]
        if _debug.logic.enabled:
            _debug.logic(
                "labels_normalised",
                labels=len(normalised),
                identical=all(label == normalised[0] for label in normalised[1:]),
            )
        if all(label == normalised[0] for label in normalised[1:]):
            return normalised[0]
        normalised.sort(key=len)

        longest_substring = ""
        for substring in common_substrings(normalised[0], normalised[1]):
            if len(substring) > len(longest_substring) and all(
                substring in label for label in normalised[2:]
            ):
                longest_substring = substring
        _debug.logic(
            "common_substring_searched",
            labels=len(normalised),
            substring_length=len(longest_substring),
        )
        return longest_substring or None

    @_debug.perf.timed
    def _create_account_model_fee(self, account_id):
        self.check_singleton()
        tolerance = self._get_payment_tolerance()
        if _debug.logic.enabled:
            _debug.logic(
                "fee_model_amounts_checked",
                stline=self,
                amount=self.amount,
                residual=self.amount_residual,
                tolerance=tolerance,
            )
        if (
            self.currency_id.compare_amounts(self.amount, 0) < 0
            or self.currency_id.compare_amounts(self.amount_residual, 0) < 0
            or (
                not float_is_zero(tolerance, 6)
                and self.currency_id.compare_amounts(
                    abs(self.amount_residual),
                    tolerance
                    * (
                        self.amount_currency
                        if self.foreign_currency_id
                        else self.amount
                    ),
                )
                > 0
            )
        ):
            return

        journal = self.journal_id
        ReconcileModel = self.env["account.reconcile.model"]
        existing = ReconcileModel.sudo()
        if existing.search_count(
            [
                ("is_bank_fee_model", "=", True),
                ("match_journal_ids", "in", journal.ids),
            ],
            limit=1,
        ):
            return

        name = f"Fees ({journal.name})"
        if existing.search_count(
            [
                ("name", "=", name),
                *self.env["account.journal"]._check_company_domain(journal.company_id),
            ],
            limit=1,
        ):
            name = f"Fees ({journal.name} - {journal.code})"

        _debug.lifecycle(
            "fee_model_creating",
            stline=self,
            journal=journal,
            name=name,
            account_id=account_id,
        )
        ReconcileModel.create(
            {
                "company_id": journal.company_id.id,
                "match_journal_ids": journal.ids,
                "name": name,
                "is_bank_fee_model": True,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account_id,
                            "label": _("Bank Fees"),
                            "amount_type": "percentage",
                            "amount_string": "100",
                        }
                    )
                ],
            }
        )

    def _is_company_amount_exceeded(
        self, company_currency, cumulated_balance, company_amount
    ):
        return (
            company_currency.compare_amounts(
                abs(cumulated_balance), abs(company_amount)
            )
            > 0
        )

    def _will_company_amount_exceed(
        self, company_currency, cumulated_balance, next_balance, company_amount
    ):
        return (
            self._is_company_amount_exceeded(
                company_currency, cumulated_balance, company_amount
            )
            and company_currency.compare_amounts(
                abs(cumulated_balance + next_balance), abs(company_amount)
            )
            > 0
        )
