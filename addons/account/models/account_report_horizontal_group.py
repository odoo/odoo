from ast import literal_eval

from odoo import api, fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class AccountReportHorizontalGroup(models.Model):
    _name = "account.report.horizontal.group"
    _description = "Horizontal group for reports"

    name = fields.Char(
        translate=True,
        required=True,
    )
    rule_ids = fields.One2many(
        comodel_name="account.report.horizontal.group.rule",
        inverse_name="horizontal_group_id",
        string="Rules",
        required=True,
    )
    report_ids = fields.Many2many(
        comodel_name="account.report",
        string="Reports",
    )

    _name_src_uniq = name_uniq_index(
        message="A horizontal group with the same name already exists.",
    )

    def _get_header_levels_data(self):
        return [
            (rule.field_name, rule._get_matching_records()) for rule in self.rule_ids
        ]


class AccountReportHorizontalGroupRule(models.Model):
    _name = "account.report.horizontal.group.rule"
    _description = "Horizontal group rule for reports"

    def _selection_move_line_relational_fields(self):
        return [
            (aml_field["name"], aml_field["string"])
            for aml_field in self.env["account.move.line"].fields_get().values()
            if aml_field["type"] in ("many2one", "many2many")
        ]

    horizontal_group_id = fields.Many2one(
        comodel_name="account.report.horizontal.group",
        index=True,
        required=True,
    )
    domain = fields.Char(
        default="[]",
        required=True,
    )
    field_name = fields.Selection(
        selection="_selection_move_line_relational_fields",
        string="Field",
        required=True,
    )
    res_model_name = fields.Char(
        string="Model",
        compute="_compute_res_model_name",
    )

    @api.depends("field_name")
    def _compute_res_model_name(self):
        for record in self:
            if record.field_name:
                record.res_model_name = (
                    self.env["account.move.line"]
                    ._fields[record.field_name]
                    .comodel_name
                )
            else:
                record.res_model_name = None

    def _get_matching_records(self):
        self.check_singleton()
        model_name = self.env["account.move.line"]._fields[self.field_name].comodel_name
        domain = literal_eval(self.domain)
        return self.env[model_name].search(domain)
