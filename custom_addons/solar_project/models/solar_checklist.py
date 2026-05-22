from odoo import fields, models


class SolarChecklistItem(models.Model):
    _name = "solar.checklist.item"
    _description = "Solar Survey / Installation Checklist Item"
    _order = "sequence, id"

    name = fields.Char(required=True, string="Item")
    task_id = fields.Many2one(
        comodel_name="project.task",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    is_done = fields.Boolean(string="Done", default=False)
    notes = fields.Text(string="Notes")
    photo_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Photo Evidence",
        ondelete="set null",
    )
