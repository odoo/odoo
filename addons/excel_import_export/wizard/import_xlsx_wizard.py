# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)


from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError


class ImportXLSXWizard(models.TransientModel):
    """This wizard is used with the template (xlsx.template) to import
    xlsx template back to active record"""

    _name = "import.xlsx.wizard"
    _description = "Wizard for importing excel"

    import_file = fields.Binary(string="Import File (*.xlsx)")
    filename = fields.Char("Import File Name")
    template_id = fields.Many2one(
        "xlsx.template",
        string="Template",
        required=True,
        ondelete="cascade",
        domain=lambda self: self._context.get("template_domain", []),
    )
    res_id = fields.Integer(string="Resource ID", readonly=True)
    res_model = fields.Char(string="Resource Model", readonly=True, size=500)
    datas = fields.Binary(string="Sample", related="template_id.datas", readonly=True)
    fname = fields.Char(
        string="Template Name", related="template_id.fname", readonly=True
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Import File(s) (*.xlsx)",
        required=True,
        help="You can select multiple files to import.",
    )
    state = fields.Selection(
        [("choose", "Choose"), ("get", "Get")],
        default="choose",
        help="* Choose: wizard show in user selection mode"
        "\n* Get: wizard show results from user action",
    )

    @api.model
    def view_init(self, fields_list):
        """This template only works on some context of active record"""
        res = super(ImportXLSXWizard, self).view_init(fields_list)
        res_model = self._context.get("active_model", False)
        res_id = self._context.get("active_id", False)
        if not res_model or not res_id:
            return res
        record = self.env[res_model].browse(res_id)
        messages = []
        valid = True
        # For all import, only allow import in draft state (for documents)
        import_states = self._context.get("template_import_states", [])
        if import_states:  # states specified in context, test this
            if "state" in record and record["state"] not in import_states:
                messages.append(_("Document must be in %s states") % import_states)
                valid = False
        else:  # no specific state specified, test with draft
            if "state" in record and "draft" not in record["state"]:  # not in
                messages.append(_("Document must be in draft state"))
                valid = False
        # Context testing
        if self._context.get("template_context", False):
            template_context = self._context["template_context"]
            for key, value in template_context.items():
                if (
                    key not in record
                    or (
                        record._fields[key].type == "many2one"
                        and record[key].id
                        or record[key]
                    )
                    != value
                ):
                    valid = False
                    messages.append(
                        _(
                            "This import action is not usable "
                            "in this document context"
                        )
                    )
                    break
        if not valid:
            raise ValidationError("\n".join(messages))
        return res

    @api.model
    def default_get(self, fields):
        res_model = self._context.get("active_model", False)
        res_id = self._context.get("active_id", False)
        template_domain = self._context.get("template_domain", [])
        templates = self.env["xlsx.template"].search(template_domain)
        if not templates:
            raise ValidationError(_("No template found"))
        defaults = super(ImportXLSXWizard, self).default_get(fields)
        for template in templates:
            if not template.datas:
                act = self.env.ref("excel_import_export.action_xlsx_template")
                raise RedirectWarning(
                    _(
                        'File "%(fname)s" not found in template, %(name)s.',
                        fname=template.fname,
                        name=template.name,
                    ),
                    act.id,
                    _("Set Templates"),
                )
        defaults["template_id"] = len(templates) == 1 and template.id or False
        defaults["res_id"] = res_id
        defaults["res_model"] = res_model
        return defaults

    def get_import_sample(self):
        self.ensure_one()
        return {
            "name": _("Import Excel"),
            "type": "ir.actions.act_window",
            "res_model": "import.xlsx.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
            "context": self._context.copy(),
        }

    def action_import(self):
        self.ensure_one()
        Import = self.env["xlsx.import"]
        res_ids = []
        if self.import_file:
            record = Import.import_xlsx(
                self.import_file, self.template_id, self.res_model, self.res_id
            )
            res_ids = [record.id]
        elif self.attachment_ids:
            for attach in self.attachment_ids:
                record = Import.import_xlsx(attach.datas, self.template_id)
                res_ids.append(record.id)
        else:
            raise ValidationError(_("Please select Excel file to import"))
        # If redirect_action is specified, do redirection
        if self.template_id.redirect_action:
            vals = self.template_id.redirect_action.read()[0]
            vals["domain"] = [("id", "in", res_ids)]
            return vals
        self.write({"state": "get"})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
