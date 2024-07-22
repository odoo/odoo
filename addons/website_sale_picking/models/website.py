# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    picking_site_ids = fields.Many2many('delivery.carrier', string='Picking sites',
                                        compute='_compute_picking_sites')

    def _compute_picking_sites(self):
        delivery_carriers = self.env['delivery.carrier'].search([('delivery_type', '=', 'onsite')])
        for website in self:
            website.picking_site_ids = delivery_carriers.filtered_domain([('website_id', '=', website.id)])
