from odoo import fields, models

# Good ratio to have a large image still small enough to stay under 5MB (common limit)
# Close to the 2:1 ratio recommended by twitter and these dimensions are recommended by meta
# https://developers.facebook.com/docs/sharing/webmasters/images/
# https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/summary-card-with-large-image
TEMPLATE_DIMENSIONS = (600, 315)
TEMPLATE_RATIO = 40 / 21


class CardCampaignTemplate(models.Model):
    _name = 'card.template'
    _description = 'Marketing Card Template'

    name = fields.Char(required=True)
    default_background = fields.Image()
    body = fields.Html(sanitize_tags=False, sanitize_attributes=False)

    primary_color = fields.Char(default='#f9f9f9', required=True)
    secondary_color = fields.Char(default='#000000', required=True)
    primary_text_color = fields.Char(default='#000000', required=True)
    secondary_text_color = fields.Char(default='#ffffff', required=True)
