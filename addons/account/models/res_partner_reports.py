from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    account_represented_company_ids = fields.One2many(
        comodel_name="res.company",
        inverse_name="account_representative_id",
    )

    def _get_followup_responsible(self, multiple_responsible=False):
        return self.env.user

    @_debug.perf.timed
    def open_customer_statement(self):
        _debug.lifecycle("open_customer_statement", records=self)
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_account_report_customer_statement"
        )
        action["params"] = {
            "options": {
                "partner_ids": (self | self.commercial_partner_id).ids,
                "unfold_all": len(self.ids) == 1,
            },
            "ignore_session": True,
        }
        return action

    @_debug.perf.timed
    def open_follow_up_report(self):
        _debug.lifecycle("open_follow_up_report", records=self)
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_account_report_followup"
        )
        action["params"] = {
            "options": {
                "partner_ids": (self | self.commercial_partner_id).ids,
                "unfold_all": len(self.ids) == 1,
            },
            "ignore_session": True,
        }
        return action

    @_debug.perf.timed
    def open_partner(self):
        _debug.lifecycle("open_partner", records=self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.id,
            "views": [[False, "form"]],
            "view_mode": "form",
            "target": "current",
        }

    @api.depends_context("show_more_partner_info")
    def _compute_display_name(self):
        if not self.env.context.get("show_more_partner_info"):
            return super()._compute_display_name()
        for partner in self:
            res = ""
            if partner.vat:
                res += f" {partner.vat},"
            if partner.country_id:
                res += f" {partner.country_id.code},"
            partner.display_name = f"{partner.name} - " + res
        return None

    def _get_partner_account_report_options(self, report, **overrides):
        """The options for `report` scoped to this partner's open entries.

        The single definition of that scope: a caller needing a variant passes
        `overrides` rather than restating the whole dict and drifting from it.
        """
        return report.get_options(
            {
                "forced_companies": self.env["res.company"]
                .search(
                    [
                        (
                            "id",
                            "child_of",
                            self.env.context.get(
                                "allowed_company_ids", self.env.company.id
                            ),
                        )
                    ]
                )
                .ids,
                "partner_ids": self.ids,
                "unfold_all": True,
                "unreconciled": True,
                "all_entries": False,
                **overrides,
            }
        )

    def _get_partner_account_report_attachment(self, report, options=None):
        self.check_singleton()
        if self.lang:
            # Print the followup in the customer's language
            report = report.with_context(lang=self.lang)

        _debug.logic(
            "statement_attachment_options",
            partner=self,
            report=report,
            lang=self.lang,
            options_given=bool(options),
        )
        if not options:
            options = self._get_partner_account_report_options(report)
        attachment_file = report.export_to_pdf(options)
        return self.env["ir.attachment"].create(
            [
                {
                    "name": f"{self.name} - {attachment_file['file_name']}",
                    "res_model": self._name,
                    "res_id": self.id,
                    "type": "binary",
                    "raw": attachment_file["file_content"],
                    "mimetype": "application/pdf",
                },
            ]
        )

    def set_commercial_partner_main(self):
        self.check_singleton()

        main_partner = self
        duplicated_partners = self.env["res.partner"].search(
            [("vat", "=", main_partner.vat), ("id", "!=", main_partner.id)]
        )
        # Update commercial partner of all duplicates
        duplicated_partners.write(
            {
                "is_company": False,
                "parent_id": main_partner.id,
                "type": "invoice",
            }
        )
        duplicated_partners_vat = self.env.context.get("duplicated_partners_vat", [])
        remaining_vats = [
            pvat for pvat in duplicated_partners_vat if pvat != main_partner.vat
        ]
        return self.env["account.ec.sales.report.handler"]._get_duplicated_vat_partners(
            remaining_vats
        )
