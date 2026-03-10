from odoo import fields, models


class ListFields(models.Model):
    _name = "list.fields"
    _description = "List Fields"

    sequence = fields.Integer()
    list_field_id = fields.Many2one(
        "ir.model.fields",
        string="Fields",
        help="add column fields for the standard list view",
    )
    list_measure_id = fields.Many2one(
        "ir.model.fields",
        string="Field ",
        help="add column fields for the standard list view",
    )
    model_id = fields.Many2one("ir.model")
    field_id = fields.Many2one(
        "dashboard.chart", ondelete="cascade", index=True, copy=False
    )
    measure_id = fields.Many2one(
        "dashboard.chart", ondelete="cascade", index=True, copy=False
    )
    value_type = fields.Selection(
        [("sum", "Sum"), ("avg", "Average")],
        string="Operation Type",
        default="sum",
        help="Set Field Value Type",
    )
