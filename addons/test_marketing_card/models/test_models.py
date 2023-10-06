
from odoo import fields, models


class MarketingCardEventPerformance(models.Model):
    """ Model that may be used in marketing cards """
    _description = 'Marketing Card Test Event Performance'
    _name = 'card.test.event.performance'
    _inherit = 'mail.thread'

    name = fields.Char()
    event_id = fields.Many2one('card.test.event')
    partner_id = fields.Many2one('res.partner')
    secret = fields.Char()

    def _marketing_card_allowed_field_paths(self):
        return [
            'name', 'partner_id', 'event_id',
            'event_id.location_id', 'event_id.image', 'event_id.location_id.tag_ids',
        ]


class MarketingCardEvent(models.Model):
    """ Model that may be used in marketing cards """
    _description = 'Marketing Card Test Event'
    _name = 'card.test.event'

    name = fields.Char()
    location_id = fields.Many2one('card.test.event.location')
    image = fields.Image()


class MarketingCardEventLocation(models.Model):
    """ Model that may be used in marketing cards """
    _description = 'Marketing Card Test Event Location'
    _name = 'card.test.event.location'

    name = fields.Char()
    manager_email = fields.Char()
    tag_ids = fields.Many2many('card.test.event.location.tag')
    secret = fields.Char()

    def _message_get_default_recipients(self):
        return {
            location: {
                'partner_ids': [],
                'email_to': location.manager_email,
                'email_cc': False,
            } for location in self
        }

    def _marketing_card_allowed_field_paths(self):
        """We allow access to 'secret' but the model isn't selectable as a render target.

        Showing allowed paths are not transitively applied through relations
        and are only valid for the render target.
        """
        return ['secret']


class MarketingCardEventLocationTags(models.Model):
    """ Model that may be used in marketing cards """
    _description = 'Marketing Card Test Event Location Tag'
    _name = 'card.test.event.location.tag'

    name = fields.Char('Name')
