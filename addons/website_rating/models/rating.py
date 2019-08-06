# -*- coding: utf-8 -*-

from odoo import fields, models, exceptions, _


class Rating(models.Model):

    _inherit = 'rating.rating'

    # Add this related field to mail.message for performance reason
    website_published = fields.Boolean(related='message_id.website_published', store=True, readonly=False)

    # Adding information for comment a rating message
    publisher_comment = fields.Text("Publisher Comment")
    publisher_id = fields.Many2one('res.partner', 'Publisher comment Author',
                                   index=True, ondelete='set null', readonly=True)
    publisher_date = fields.Datetime("Date of the publisher comment", readonly=True)

    def write(self, values):
        if values.get('publisher_comment'):
            if not self.env.user.has_group("website.group_website_publisher"):
                raise exceptions.AccessError(_("Only the publisher of the website can change the rating comment"))
            values['publisher_date'] = fields.Datetime.now()
            values['publisher_id'] = int(self.env.user.partner_id)
        return super(Rating, self).write(values)
