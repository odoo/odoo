from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    picking_site_ids = fields.Many2many(
        'delivery.carrier',
        string='Picking sites'
    )
