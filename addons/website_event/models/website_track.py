from odoo import fields, models


class WebsiteTrack(models.Model):
    _inherit = 'website.track'

    event_id = fields.Many2one(
        comodel_name='event.event', ondelete='cascade', readonly=True, index='btree_not_null',
    )
