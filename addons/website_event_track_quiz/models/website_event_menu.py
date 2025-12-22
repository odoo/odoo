from odoo import fields, models


class WebsiteEventMenu(models.Model):
    _inherit = "website.event.menu"

    menu_type = fields.Selection(
        selection_add=[('community', 'Community Menu')], ondelete={'community': 'cascade'})
