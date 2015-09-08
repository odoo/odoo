# -*- coding: utf-8 -*-
from openerp import fields, models


class Rating(models.Model):

    _inherit = 'rating.rating'

    # Add this related field to mail.message for performance reason
    # This field may one day be deplaced to another module (like 'website_rating') if it is required for
    # another usage not related to website_sale.
    website_published = fields.Boolean(related='message_id.website_published', store=True)
