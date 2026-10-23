from odoo import fields, models, api


class EgResPartner(models.Model):
    _name = "eg.res.partner"

    odoo_partner_id = fields.Many2one(comodel_name="res.partner", string="Odoo Customer", required=True)
    name = fields.Char(related="odoo_partner_id.name", string="Name", store=True, readonly=True)
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance", required=True)
    provider = fields.Selection(related="instance_id.provider", store=True)
    inst_partner_id = fields.Char(string="Instance Partner", required=True)
    update_required = fields.Boolean(string="Update Required")

    # add by akash
    customer_image = fields.Binary(string='Image')
