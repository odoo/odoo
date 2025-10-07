from odoo import models, fields, api


class EgInventoryLocation(models.Model):
    _name = "eg.inventory.location"

    location_id = fields.Char(string="Location ID")
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    update_required = fields.Boolean(string="Update Required")
    city = fields.Char(string="City")
    name = fields.Char(string="Name")
