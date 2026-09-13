from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class SlideTag(models.Model):
    _name = "slide.tag"
    _description = "Slide Tag"

    name = fields.Char(
        translate=True,
        required=True,
    )

    _name_src_uniq = name_uniq_index(
        message="A tag must be unique!",
    )
