# -*- coding: utf-8 -*-
from odoo import fields, models


class Rating(models.Model):

    _inherit = 'rating.rating'

    # Add this related field to mail.message for performance reason
    website_published = fields.Boolean(related='message_id.website_published', store=True, readonly=False)
