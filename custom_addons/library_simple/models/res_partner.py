# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    """Inherit res.partner to add a link to their favorite book."""
    # Internal Reference: _inherit tells the ORM to modify the existing 'res.partner' model
    _inherit = 'res.partner'

    # Add a new field to the existing model
    # Internal Reference: Many2one creates a foreign key relationship
    favorite_book_id = fields.Many2one(
        comodel_name='library.book', # Target model defined in this module
        string='Favorite Book',
        help="The user's favorite book from the library."
    )