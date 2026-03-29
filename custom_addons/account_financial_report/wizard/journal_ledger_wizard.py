# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class JournalLedgerReportWizard(models.TransientModel):
    """Journal Ledger report wizard."""

    _name = "journal.ledger.report.wizard"
    _description = "Journal Ledger Report Wizard"
    _inherit = "account_financial_report_abstract_wizard"

    date_range_id = fields.Many2one(comodel_name="date.range", string="Date range")
    date_from = fields.Date(string="Start date", required=True)
    date_to = fields.Date(string="End date", required=True)
    journal_ids = fields.Many2many(
        comodel_name="account.journal", string="Journals", required=False
    )
    move_target = fields.Selection(
        selection="_get_move_targets", default="posted", required=True
    )
    foreign_currency = fields.Boolean()
    sort_option = fields.Selection(
        selection="_get_sort_options",
        string="Sort entries by",
        default="move_name",
        required=True,
    )
    group_option = fields.Selection(
        selection="_get_group_options",
        string="Group entries by",
        default="journal",
        required=True,
    )
    with_account_name = fields.Boolean(default=False)
    with_auto_sequence = fields.Boolean(string="Show Auto Sequence", default=False)

    @api.model
    def _get_move_targets(self):
        return [
            ("all", self.env._("All")),
            ("posted", self.env._("Posted")),
            ("draft", self.env._("Not Posted")),
        ]

    @api.model
    def _get_sort_options(self):
        return [("move_name", self.env._("Entry number")), ("date", self.env._("Date"))]

    @api.model
    def _get_group_options(self):
        return [("journal", self.env._("Journal")), ("none", self.env._("No group"))]

    @api.onchange("date_range_id")
    def onchange_date_range_id(self):
        self.date_from = self.date_range_id.date_start
        self.date_to = self.date_range_id.date_end

    @api.onchange("company_id")
    def onchange_company_id(self):
        """Handle company change."""
        if (
            self.company_id
            and self.date_range_id.company_id
            and self.date_range_id.company_id != self.company_id
        ):
            self.date_range_id = False
        if self.company_id and self.journal_ids:
            self.journal_ids = self.journal_ids.filtered(
                lambda p: p.company_id == self.company_id or not p.company_id
            )
        res = {"domain": {"journal_ids": []}}
        if not self.company_id:
            return res
        else:
            res["domain"]["journal_ids"] += [("company_id", "=", self.company_id.id)]
        return res

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_report_journal_ledger()
        if report_type == "xlsx":
            report_name = "a_f_r.report_journal_ledger_xlsx"
        else:
            report_name = "account_financial_report.journal_ledger"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, data=data)
        )

    def _prepare_report_journal_ledger(self):
        self.ensure_one()
        journals = self.journal_ids
        if not journals:
            # Not selecting a journal means that we'll display all journals
            journals = self.env["account.journal"].search(
                [("company_id", "=", self.company_id.id)]
            )
        return {
            "wizard_id": self.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "move_target": self.move_target,
            "foreign_currency": self.foreign_currency,
            "company_id": self.company_id.id,
            "journal_ids": journals.ids,
            "sort_option": self.sort_option,
            "group_option": self.group_option,
            "with_account_name": self.with_account_name,
            "account_financial_report_lang": self.env.lang,
            "with_auto_sequence": self.with_auto_sequence,
        }

    def _export(self, report_type):
        """Default export is PDF."""
        self.ensure_one()
        return self._print_report(report_type)

    @api.model
    def _get_ml_tax_description(
        self, move_line_data, tax_line_data, move_line_taxes_data
    ):
        taxes_description = ""
        if move_line_data["tax_line_id"]:
            taxes_description = tax_line_data["description"] or tax_line_data["name"]
        elif move_line_taxes_data:
            tax_names = []
            for tax_key in move_line_taxes_data:
                tax = move_line_taxes_data[tax_key]
                tax_names.append(tax["description"] or tax["name"])
            taxes_description = ",".join(tax_names)
        return taxes_description

    @api.model
    def _get_partner_name(self, partner_id, partner_data):
        if partner_id in partner_data.keys():
            return partner_data[partner_id]["name"]
        else:
            return ""

    @api.model
    def _get_atr_from_dict(self, obj_id, data, key):
        try:
            return data[obj_id][key]
        except KeyError:
            return data[str(obj_id)][key]

    @api.model
    def _get_data_from_dict(self, obj_id, data):
        if data:
            if isinstance(list(data.keys())[0], int):
                return data.get(obj_id, False)
            else:
                return data.get(obj_id(obj_id), False)
        else:
            return False
