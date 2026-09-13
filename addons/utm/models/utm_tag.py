from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class UtmTag(models.Model):
    """Model of categories of utm campaigns, i.e. marketing, newsletter, ..."""

    _name = "utm.tag"
    _inherit = ["mixin.color"]
    _description = "UTM Tag"
    _order = "name"

    name = fields.Char(
        translate=True,
        required=True,
    )
    color = fields.Integer(
        string="Color Index",
        default=lambda self: self._default_color(),
        help="Tag color. No color means no display in kanban to distinguish internal tags from public categorization tags.",
    )

    _name_src_uniq = name_uniq_index(
        message="Tag name already exists!",
    )
