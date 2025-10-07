# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import base64
import os
from ast import literal_eval
from os.path import join as opj

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_path

from . import common as co


class XLSXTemplate(models.Model):
    """Master Data for XLSX Templates
    - Excel Template
    - Import/Export Meta Data (dict text)
    - Default values, etc.
    """

    _name = "xlsx.template"
    _description = "Excel template file and instruction"
    _order = "name"

    name = fields.Char(string="Template Name", required=True)
    res_model = fields.Char(
        string="Resource Model",
        help="The database object this attachment will be attached to.",
    )
    fname = fields.Char(string="File Name")
    gname = fields.Char(
        string="Group Name",
        help="Multiple template of same model, can belong to same group,\n"
        "result in multiple template selection",
    )
    description = fields.Char()
    input_instruction = fields.Text(
        string="Instruction (Input)",
        help="This is used to construct instruction in tab Import/Export",
    )
    instruction = fields.Text(
        compute="_compute_output_instruction",
        help="Instruction on how to import/export, prepared by system.",
    )
    datas = fields.Binary(string="File Content")
    to_csv = fields.Boolean(
        string="Convert to CSV?",
        default=False,
        help="Convert file into CSV format on export",
    )
    csv_delimiter = fields.Char(
        string="CSV Delimiter",
        size=1,
        default=",",
        required=True,
        help="Optional for CSV, default is comma.",
    )
    csv_extension = fields.Char(
        string="CSV File Extension",
        size=5,
        default="csv",
        required=True,
        help="Optional for CSV, default is .csv",
    )
    csv_quote = fields.Boolean(
        string="CSV Quoting",
        default=True,
        help="Optional for CSV, default is full quoting.",
    )
    export_ids = fields.One2many(
        comodel_name="xlsx.template.export", inverse_name="template_id"
    )
    import_ids = fields.One2many(
        comodel_name="xlsx.template.import", inverse_name="template_id"
    )
    post_import_hook = fields.Char(
        string="Post Import Function Hook",
        help="Call a function after successful import, i.e.,\n"
        "${object.post_import_do_something()}",
    )
    show_instruction = fields.Boolean(
        string="Show Output",
        default=False,
        help="This is the computed instruction based on tab Import/Export,\n"
        "to be used by xlsx import/export engine",
    )
    redirect_action = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Return Action",
        domain=[("type", "=", "ir.actions.act_window")],
        help="Optional action, redirection after finish import operation",
    )
    # Utilities
    export_action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        ondelete="set null",
    )
    import_action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        ondelete="set null",
    )
    use_report_wizard = fields.Boolean(
        string="Easy Reporting",
        help="Use common report wizard model, instead of create specific model",
    )
    result_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Report Model",
        help="When use commone wizard, choose the result model",
    )
    result_field = fields.Char(
        compute="_compute_result_field",
    )
    report_menu_id = fields.Many2one(
        comodel_name="ir.ui.menu",
        string="Report Menu",
        readonly=True,
    )
    report_action_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Report Action",
    )

    def _compute_result_field(self):
        for rec in self:
            rec.result_field = (
                ("x_%s_results" % rec.id) if rec.result_model_id else False
            )

    @api.constrains("redirect_action", "res_model")
    def _check_action_model(self):
        for rec in self:
            if (
                rec.res_model
                and rec.redirect_action
                and rec.res_model != rec.redirect_action.res_model
            ):
                raise ValidationError(
                    _("The selected redirect action is " "not for model %s")
                    % rec.res_model
                )

    @api.model
    def load_xlsx_template(self, template_ids, addon=False):
        for template in self.browse(template_ids):
            if not addon:
                addon = list(template.get_external_id().values())[0].split(".")[0]
            addon_path = get_module_path(addon)
            file_path = False
            for root, _dirs, files in os.walk(addon_path):
                for name in files:
                    if name == template.fname:
                        file_path = os.path.abspath(opj(root, name))
            if file_path:
                template.datas = base64.b64encode(open(file_path, "rb").read())
        return True

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            if rec.input_instruction:
                rec._compute_input_export_instruction()
                rec._compute_input_import_instruction()
                rec._compute_input_post_import_hook()
            if rec.result_model_id:
                rec._update_result_field_common_wizard()
                rec._update_result_export_ids()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get("input_instruction"):
            for rec in self:
                rec._compute_input_export_instruction()
                rec._compute_input_import_instruction()
                rec._compute_input_post_import_hook()
        if vals.get("result_model_id"):
            for rec in self:
                rec._update_result_field_common_wizard()
                rec._update_result_export_ids()
        return res

    def unlink(self):
        self.env["ir.model.fields"].search(
            [
                ("model", "=", "report.xlsx.wizard"),
                ("name", "=", self.mapped("result_field")),
            ]
        ).unlink()
        return super().unlink()

    def _update_result_field_common_wizard(self):
        self.ensure_one()
        _model = self.env["ir.model"].search([("model", "=", "report.xlsx.wizard")])
        _model.ensure_one()
        _field = self.env["ir.model.fields"].search(
            [("model", "=", "report.xlsx.wizard"), ("name", "=", self.result_field)]
        )
        if not _field:
            _field = self.env["ir.model.fields"].create(
                {
                    "model_id": _model.id,
                    "name": self.result_field,
                    "field_description": "Results",
                    "ttype": "many2many",
                    "relation": self.result_model_id.model,
                    "store": False,
                    "depends": "res_model",
                }
            )
        else:
            _field.ensure_one()
            _field.write({"relation": self.result_model_id.model})
        _field.compute = """
self['{}'] = self.env['{}'].search(self.safe_domain(self.domain))
        """.format(
            self.result_field,
            self.result_model_id.model,
        )

    def _update_result_export_ids(self):
        self.ensure_one()
        results = self.env["xlsx.template.export"].search(
            [("template_id", "=", self.id), ("row_field", "=", self.result_field)]
        )
        if not results:
            self.export_ids.unlink()
            self.write(
                {
                    "export_ids": [
                        (0, 0, {"sequence": 10, "section_type": "sheet", "sheet": 1}),
                        (
                            0,
                            0,
                            {
                                "sequence": 20,
                                "section_type": "row",
                                "row_field": self.result_field,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "sequence": 30,
                                "section_type": "data",
                                "excel_cell": "A1",
                                "field_name": "id",
                            },
                        ),
                    ],
                }
            )

    @api.onchange("use_report_wizard")
    def _onchange_use_report_wizard(self):
        self.res_model = "report.xlsx.wizard" if self.use_report_wizard else False
        self.redirect_action = False

    def _compute_input_export_instruction(self):
        self = self.with_context(compute_from_input=True)
        for rec in self:
            # Export Instruction
            input_dict = literal_eval(rec.input_instruction.strip())
            rec.export_ids.unlink()
            export_dict = input_dict.get("__EXPORT__")
            if not export_dict:
                continue
            export_lines = []
            sequence = 0
            # Sheet
            for sheet, rows in export_dict.items():
                sequence += 1
                vals = {
                    "sequence": sequence,
                    "section_type": "sheet",
                    "sheet": str(sheet),
                }
                export_lines.append((0, 0, vals))
                # Rows
                for row_field, lines in rows.items():
                    sequence += 1
                    is_cont = False
                    if "_CONT_" in row_field:
                        is_cont = True
                        row_field = row_field.replace("_CONT_", "")
                    is_extend = False
                    if "_EXTEND_" in row_field:
                        is_extend = True
                        row_field = row_field.replace("_EXTEND_", "")
                    vals = {
                        "sequence": sequence,
                        "section_type": (row_field == "_HEAD_" and "head" or "row"),
                        "row_field": row_field,
                        "is_cont": is_cont,
                        "is_extend": is_extend,
                    }
                    export_lines.append((0, 0, vals))
                    for excel_cell, field_name in lines.items():
                        sequence += 1
                        vals = {
                            "sequence": sequence,
                            "section_type": "data",
                            "excel_cell": excel_cell,
                            "field_name": field_name,
                        }
                        export_lines.append((0, 0, vals))
            rec.write({"export_ids": export_lines})

    def _compute_input_import_instruction(self):
        self = self.with_context(compute_from_input=True)
        for rec in self:
            # Import Instruction
            input_dict = literal_eval(rec.input_instruction.strip())
            rec.import_ids.unlink()
            import_dict = input_dict.get("__IMPORT__")
            if not import_dict:
                continue
            import_lines = []
            sequence = 0
            # Sheet
            for sheet, rows in import_dict.items():
                sequence += 1
                vals = {
                    "sequence": sequence,
                    "section_type": "sheet",
                    "sheet": str(sheet),
                }
                import_lines.append((0, 0, vals))
                # Rows
                for row_field, lines in rows.items():
                    sequence += 1
                    no_delete = False
                    if "_NODEL_" in row_field:
                        no_delete = True
                        row_field = row_field.replace("_NODEL_", "")
                    vals = {
                        "sequence": sequence,
                        "section_type": (row_field == "_HEAD_" and "head" or "row"),
                        "row_field": row_field,
                        "no_delete": no_delete,
                    }
                    import_lines.append((0, 0, vals))
                    for excel_cell, field_name in lines.items():
                        sequence += 1
                        vals = {
                            "sequence": sequence,
                            "section_type": "data",
                            "excel_cell": excel_cell,
                            "field_name": field_name,
                        }
                        import_lines.append((0, 0, vals))
            rec.write({"import_ids": import_lines})

    def _compute_input_post_import_hook(self):
        self = self.with_context(compute_from_input=True)
        for rec in self:
            # Import Instruction
            input_dict = literal_eval(rec.input_instruction.strip())
            rec.post_import_hook = input_dict.get("__POST_IMPORT__")

    def _compose_field_name(self, line):
        field_name = line.field_name or ""
        field_name += line.field_cond or ""
        field_name += line.style or ""
        field_name += line.style_cond or ""
        if line.is_sum:
            field_name += "@{sum}"
        return field_name

    def _compute_output_instruction(self):
        """From database, compute back to dictionary"""
        for rec in self:
            inst_dict = {}
            prev_sheet = False
            prev_row = False
            # Export Instruction
            itype = "__EXPORT__"
            inst_dict[itype] = {}
            for line in rec.export_ids:
                if line.section_type == "sheet":
                    sheet = co.isinteger(line.sheet) and int(line.sheet) or line.sheet
                    sheet_dict = {sheet: {}}
                    inst_dict[itype].update(sheet_dict)
                    prev_sheet = sheet
                    continue
                if line.section_type in ("head", "row"):
                    row_field = line.row_field
                    if line.section_type == "row" and line.is_cont:
                        row_field = "_CONT_%s" % row_field
                    if line.section_type == "row" and line.is_extend:
                        row_field = "_EXTEND_%s" % row_field
                    row_dict = {row_field: {}}
                    inst_dict[itype][prev_sheet].update(row_dict)
                    prev_row = row_field
                    continue
                if line.section_type == "data":
                    excel_cell = line.excel_cell
                    field_name = self._compose_field_name(line)
                    cell_dict = {excel_cell: field_name}
                    inst_dict[itype][prev_sheet][prev_row].update(cell_dict)
                    continue
            # Import Instruction
            itype = "__IMPORT__"
            inst_dict[itype] = {}
            for line in rec.import_ids:
                if line.section_type == "sheet":
                    sheet = co.isinteger(line.sheet) and int(line.sheet) or line.sheet
                    sheet_dict = {sheet: {}}
                    inst_dict[itype].update(sheet_dict)
                    prev_sheet = sheet
                    continue
                if line.section_type in ("head", "row"):
                    row_field = line.row_field
                    if line.section_type == "row" and line.no_delete:
                        row_field = "_NODEL_%s" % row_field
                    row_dict = {row_field: {}}
                    inst_dict[itype][prev_sheet].update(row_dict)
                    prev_row = row_field
                    continue
                if line.section_type == "data":
                    excel_cell = line.excel_cell
                    field_name = line.field_name or ""
                    field_name += line.field_cond or ""
                    cell_dict = {excel_cell: field_name}
                    inst_dict[itype][prev_sheet][prev_row].update(cell_dict)
                    continue
            itype = "__POST_IMPORT__"
            inst_dict[itype] = False
            if rec.post_import_hook:
                inst_dict[itype] = rec.post_import_hook
            rec.instruction = inst_dict

    def _get_export_action_domain(self, model):
        return [
            ("binding_model_id", "=", model.id),
            ("res_model", "=", "export.xlsx.wizard"),
            ("name", "=", "Export Excel"),
        ]

    def _get_export_action(self, model):
        export_action_domain = self._get_export_action_domain(model)
        return self.env["ir.actions.act_window"].search(export_action_domain, limit=1)

    def _create_export_action(self, model):
        vals = {
            "name": "Export Excel",
            "res_model": "export.xlsx.wizard",
            "binding_model_id": model.id,
            "binding_type": "action",
            "target": "new",
            "view_mode": "form",
            "context": """
                {'template_domain': [('res_model', '=', '%s'),
                                    ('export_action_id', '!=', False),
                                    ('gname', '=', False)]}
            """
            % (self.res_model),
        }
        return self.env["ir.actions.act_window"].create(vals)

    def add_export_action(self):
        self.ensure_one()
        model = self.env["ir.model"].search([("model", "=", self.res_model)], limit=1)
        export_action = self._get_export_action(model)
        if not export_action:
            export_action = self._create_export_action(model)
        self.export_action_id = export_action

    def remove_export_action(self):
        self.ensure_one()
        export_action = self.export_action_id
        self.export_action_id = False
        if not self.search(
            [
                ("res_model", "=", self.res_model),
                ("export_action_id", "=", export_action.id),
            ]
        ):
            export_action.unlink()

    def add_import_action(self):
        self.ensure_one()
        vals = {
            "name": "Import Excel",
            "res_model": "import.xlsx.wizard",
            "binding_model_id": self.env["ir.model"]
            .search([("model", "=", self.res_model)])
            .id,
            "binding_type": "action",
            "target": "new",
            "view_mode": "form",
            "context": """
                {'template_domain': [('res_model', '=', '%s'),
                                     ('fname', '=', '%s'),
                                     ('gname', '=', False)]}
            """
            % (self.res_model, self.fname),
        }
        action = self.env["ir.actions.act_window"].create(vals)
        self.import_action_id = action

    def remove_import_action(self):
        self.ensure_one()
        if self.import_action_id:
            self.import_action_id.unlink()

    def add_report_menu(self):
        self.ensure_one()
        if not self.fname:
            raise UserError(_("No file content!"))
        # Create report action
        vals = {
            "name": self.name,
            "report_type": "excel",
            "model": "report.xlsx.wizard",
            "report_name": self.fname,
            "report_file": self.fname,
        }
        report_action = self.env["ir.actions.report"].create(vals)
        self.report_action_id = report_action
        # Create window action
        vals = {
            "name": self.name,
            "res_model": "report.xlsx.wizard",
            "binding_type": "action",
            "target": "new",
            "view_mode": "form",
            "context": {
                "report_action_id": report_action.id,
                "default_res_model": self.result_model_id.model,
            },
        }
        action = self.env["ir.actions.act_window"].create(vals)
        # Create menu
        vals = {
            "name": self.name,
            "action": "{},{}".format(action._name, action.id),
        }
        menu = self.env["ir.ui.menu"].create(vals)
        self.report_menu_id = menu

    def remove_report_menu(self):
        self.ensure_one()
        if self.report_action_id:
            self.report_action_id.unlink()
        if self.report_menu_id:
            self.report_menu_id.action.unlink()
            self.report_menu_id.unlink()


class XLSXTemplateImport(models.Model):
    _name = "xlsx.template.import"
    _description = "Detailed of how excel data will be imported"
    _order = "sequence"

    template_id = fields.Many2one(
        comodel_name="xlsx.template",
        string="XLSX Template",
        index=True,
        ondelete="cascade",
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    sheet = fields.Char()
    section_type = fields.Selection(
        [("sheet", "Sheet"), ("head", "Head"), ("row", "Row"), ("data", "Data")],
        required=True,
    )
    row_field = fields.Char(help="If section type is row, this field is required")
    no_delete = fields.Boolean(
        default=False,
        help="By default, all rows will be deleted before import.\n"
        "Select No Delete, otherwise",
    )
    excel_cell = fields.Char(string="Cell")
    field_name = fields.Char(string="Field")
    field_cond = fields.Char(string="Field Cond.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._extract_field_name(vals)
        return super().create(vals_list)

    @api.model
    def _extract_field_name(self, vals):
        if self._context.get("compute_from_input") and vals.get("field_name"):
            field_name, field_cond = co.get_field_condition(vals["field_name"])
            field_cond = field_cond and "${%s}" % (field_cond or "") or False
            vals.update({"field_name": field_name, "field_cond": field_cond})
        return vals


class XLSXTemplateExport(models.Model):
    _name = "xlsx.template.export"
    _description = "Detailed of how excel data will be exported"
    _order = "sequence"

    template_id = fields.Many2one(
        comodel_name="xlsx.template",
        string="XLSX Template",
        index=True,
        ondelete="cascade",
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    sheet = fields.Char()
    section_type = fields.Selection(
        [("sheet", "Sheet"), ("head", "Head"), ("row", "Row"), ("data", "Data")],
        required=True,
    )
    row_field = fields.Char(help="If section type is row, this field is required")
    is_cont = fields.Boolean(
        string="Continue", default=False, help="Continue data rows after last data row"
    )
    is_extend = fields.Boolean(
        string="Extend",
        default=False,
        help="Extend a blank row after filling each record, to extend the footer",
    )
    excel_cell = fields.Char(string="Cell")
    field_name = fields.Char(string="Field")
    field_cond = fields.Char(string="Field Cond.")
    is_sum = fields.Boolean(string="Sum", default=False)
    style = fields.Char(string="Default Style")
    style_cond = fields.Char(string="Style w/Cond.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._extract_field_name(vals)
        return super().create(vals_list)

    @api.model
    def _extract_field_name(self, vals):
        if self._context.get("compute_from_input") and vals.get("field_name"):
            field_name, field_cond = co.get_field_condition(vals["field_name"])
            field_cond = field_cond or 'value or ""'
            field_name, style = co.get_field_style(field_name)
            field_name, style_cond = co.get_field_style_cond(field_name)
            field_name, func = co.get_field_aggregation(field_name)
            vals.update(
                {
                    "field_name": field_name,
                    "field_cond": "${%s}" % (field_cond or ""),
                    "style": "#{%s}" % (style or ""),
                    "style_cond": "#?%s?" % (style_cond or ""),
                    "is_sum": func == "sum" and True or False,
                }
            )
        return vals
