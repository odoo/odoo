# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class WebsiteDuplicate(models.TransientModel):
    _name = 'website.duplicate'
    _description = "Duplicate Websites"

    name = fields.Char(string="Website Name", required=True)

    def action_duplicate(self):
        websites = self.env['website'].browse(self.env.context.get('active_ids'))
        for count, website in enumerate(websites, start=1):
            website.copy({'name': self.name if count == 1 else f"{self.name} {count}"})
