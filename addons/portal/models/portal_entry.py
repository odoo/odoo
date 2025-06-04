from odoo import fields, models


class PortalEntry(models.Model):
    _name = "portal.entry"
    _description = "Portal Entry"
    _order = "sequence, id"

    name = fields.Char("Title of Card", required=True, translate=True)
    url = fields.Char("Target URL")
    description = fields.Text("Description of Card", translate=True)
    image = fields.Binary("Image")
    sequence = fields.Integer("sequence", default="999")
    placeholder_count = fields.Char("Placeholder Count")
    category = fields.Char("Category", default="common_category")
    show_in_portal = fields.Boolean("Show in Portal", default=True)
    is_config_card = fields.Boolean("Config Card", default=False)

    # Override me to add custom logic
    def should_show_portal_card(self):
        return self.is_config_card
