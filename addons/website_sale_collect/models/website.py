# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    in_store_dm_id = fields.Many2one(
        string="In-store Delivery Method",
        comodel_name='delivery.carrier',
        compute='_compute_in_store_dm_id',
    )

    def _compute_in_store_dm_id(self):
        in_store_delivery_methods = self.env['delivery.carrier'].search(
            [('delivery_type', '=', 'in_store'), ('is_published', '=', True)]
        )
        for website in self:
            website.in_store_dm_id = in_store_delivery_methods.filtered_domain([
               '|', ('website_id', '=', False), ('website_id', '=', website.id),
               '|', ('company_id', '=', False), ('company_id', '=', website.company_id.id),
            ])[:1]
