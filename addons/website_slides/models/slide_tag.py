from odoo import fields, models


class SlideTag(models.Model):
    """ Tag to search slides across channels. """
    _name = 'slide.tag'
    _description = 'Slide Tag'

    name = fields.Char('Name', required=True, translate=True)

    _slide_tag_unique = models.Constraint(
        'UNIQUE(name)',
        'A tag must be unique!',
    )
