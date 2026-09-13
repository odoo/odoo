from odoo import fields, models


class ReportLayout(models.Model):
    _name = "report.layout"
    _description = "Report Layout"
    _order = "sequence, id"

    view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Document Template",
        required=True,
        ondelete="cascade",
    )
    image = fields.Char(string="Preview image src")
    pdf = fields.Char(string="Preview pdf src")

    sequence = fields.Integer(default=50)
    name = fields.Char()
