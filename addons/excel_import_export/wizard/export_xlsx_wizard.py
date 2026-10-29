# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class ExportXLSXWizard(models.TransientModel):
    """This wizard is used with the template (xlsx.template) to export
    xlsx template filled with data form the active record"""

    _name = "export.xlsx.wizard"
    _description = "Wizard for exporting excel"

    name = fields.Char(string="File Name", readonly=True, size=500)
    data = fields.Binary(string="File", readonly=True)
    template_id = fields.Many2one(
        "xlsx.template",
        string="Template",
        required=True,
        ondelete="cascade",
        domain=lambda self: self._context.get("template_domain", []),
    )
    res_ids = fields.Char(string="Resource IDs", readonly=True, required=True)
    res_model = fields.Char(
        string="Resource Model", readonly=True, required=True, size=500
    )
    state = fields.Selection(
        [("choose", "Choose"), ("get", "Get")],
        default="choose",
        help="* Choose: wizard show in user selection mode"
        "\n* Get: wizard show results from user action",
    )

    @api.model
    def default_get(self, fields):
        res_model = self._context.get("active_model", False)
        res_ids = self._context.get("active_ids", False)
        template_domain = self._context.get("template_domain", [])
        templates = self.env["xlsx.template"].search(template_domain)
        if not templates:
            raise ValidationError(_("No template found"))
        defaults = super(ExportXLSXWizard, self).default_get(fields)
        for template in templates:
            if not template.datas:
                raise ValidationError(_("No file in %s") % (template.name,))
        defaults["template_id"] = len(templates) == 1 and templates.id or False
        defaults["res_ids"] = ",".join([str(x) for x in res_ids])
        defaults["res_model"] = res_model
        return defaults

    def action_export(self):
        self.ensure_one()
        Export = self.env["xlsx.export"]
        out_file, out_name = Export.export_xlsx(
            self.template_id, self.res_model, safe_eval(self.res_ids)
        )
        self.write({"state": "get", "data": out_file, "name": out_name})
        return {
            "type": "ir.actions.act_window",
            "res_model": "export.xlsx.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
