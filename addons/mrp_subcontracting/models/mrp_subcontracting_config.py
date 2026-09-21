from odoo import fields, models


class MrpSubcontractingConfig(models.Model):
    _name = "mrp_subcontracting.config"
    _description = "A company's mrp subcontracting configuration"
    _inherit = ["mixin.company.config"]

    subcontracting_location_id = fields.Many2one(comodel_name="stock.location")
