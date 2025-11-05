# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class UomUom(models.Model):
    _inherit = 'uom.uom'

    website_ids = fields.Many2many(
        'website',
        string="Websites",
        help="Websites where this UoM is used.",
    )

    def _is_website_available(self):
        return not self.website_ids or self.env['website'].get_current_website() in self.website_ids
