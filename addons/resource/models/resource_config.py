from odoo import fields, models


class ResourceConfig(models.Model):
    _name = "resource.config"
    _description = "A company's resource configuration"
    _inherit = ["mixin.company.config"]

    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Default Working Hours",
        ondelete="restrict",
        check_company=True,
    )
