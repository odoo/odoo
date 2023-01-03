# -*- coding: utf-8 -*-

from odoo import fields, models, exceptions, _


class Rating(models.Model):
    _inherit = 'rating.rating'

    # Adding information for comment a rating message
    publisher_comment = fields.Text("Publisher comment")
    publisher_id = fields.Many2one('res.partner', 'Commented by',
                                   ondelete='set null', readonly=True)
    publisher_datetime = fields.Datetime("Commented on", readonly=True)

    def write(self, values):
        if values.get('publisher_comment'):
            if not self.env.user.has_group("website.group_website_restricted_editor"):
                raise exceptions.AccessError(_("Only the publisher of the website can change the rating comment"))
            if not values.get('publisher_datetime'):
                values['publisher_datetime'] = fields.Datetime.now()
            if not values.get('publisher_id'):
                values['publisher_id'] = self.env.user.partner_id.id
        return super(Rating, self).write(values)
