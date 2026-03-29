# Copyright 2019 Lorenzo Battistini @ TAKOBI
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AbstractWizard(models.AbstractModel):
    _name = "account_financial_report_abstract_wizard"
    _description = "Abstract Wizard"

    def _get_partner_ids_domain(self):
        return [
            "&",
            "|",
            ("company_id", "=", self.company_id.id),
            ("company_id", "=", False),
            "|",
            ("parent_id", "=", False),
            ("is_company", "=", True),
        ]

    def _default_partners(self):
        context = self.env.context
        if context.get("active_ids") and context.get("active_model") == "res.partner":
            partners = self.env["res.partner"].browse(context["active_ids"])
            corp_partners = partners.filtered("parent_id")
            partners -= corp_partners
            partners |= corp_partners.mapped("commercial_partner_id")
            return partners.ids

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=False,
        string="Company",
    )

    def button_export_html(self):
        self.ensure_one()
        report_type = "qweb-html"
        return self._export(report_type)

    def button_export_pdf(self):
        self.ensure_one()
        report_type = "qweb-pdf"
        return self._export(report_type)

    def button_export_xlsx(self):
        self.ensure_one()
        report_type = "xlsx"
        return self._export(report_type)
