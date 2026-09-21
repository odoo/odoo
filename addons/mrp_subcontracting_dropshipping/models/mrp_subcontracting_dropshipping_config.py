from odoo import fields, models


class MrpSubcontractingDropshippingConfig(models.Model):
    _name = "mrp_subcontracting_dropshipping.config"
    _description = "A company's mrp subcontracting dropshipping configuration"
    _inherit = ["mixin.company.config"]

    dropship_subcontractor_pick_type_id = fields.Many2one(
        comodel_name="stock.picking.type"
    )
