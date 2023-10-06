from odoo import fields, models

# Good ratio to have a large image still small enough to stay under 5MB (common limit)
# Close to the 2:1 ratio recommended by twitter and these dimensions are recommended by meta
# https://developers.facebook.com/docs/sharing/webmasters/images/
# https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/summary-card-with-large-image
TEMPLATE_DIMENSIONS = (1200, 630)
TEMPLATE_RATIO = 40 / 21

class CardCampaignTemplate(models.Model):
    _name = 'card.template'
    _description = 'Marketing Card Template'

    name = fields.Char(required=True, translate=True)
    default_background = fields.Image()
    body = fields.Html(sanitize=False)
