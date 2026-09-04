# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class XLSXReport(models.AbstractModel):
    """Common class for xlsx reporting wizard"""

    _name = "xlsx.report"
    _description = "Excel Report AbstractModel"

    name = fields.Char(string="File Name", readonly=True, size=500)
    data = fields.Binary(string="File", readonly=True)
    template_id = fields.Many2one(
        "xlsx.template",
        string="Template",
        required=True,
        ondelete="cascade",
        domain=lambda self: self._context.get("template_domain", []),
    )
    choose_template = fields.Boolean(string="Allow Choose Template", default=False)
    state = fields.Selection(
        [("choose", "Choose"), ("get", "Get")],
        default="choose",
        help="* Choose: wizard show in user selection mode"
        "\n* Get: wizard show results from user action",
    )

    @api.model
    def default_get(self, fields):
        template_domain = self._context.get("template_domain", [])
        templates = self.env["xlsx.template"].search(template_domain)
        if not templates:
            raise ValidationError(_("No template found"))
        defaults = super(XLSXReport, self).default_get(fields)
        for template in templates:
            if not template.datas:
                raise ValidationError(_("No file in %s") % (template.name,))
        defaults["template_id"] = len(templates) == 1 and templates.id or False
        return defaults

    def report_xlsx(self):
        self.ensure_one()
        Export = self.env["xlsx.export"]
        out_file, out_name = Export.export_xlsx(self.template_id, self._name, self.id)
        self.write({"state": "get", "data": out_file, "name": out_name})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
