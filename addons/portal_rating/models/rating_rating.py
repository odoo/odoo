# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _


class Rating(models.Model):
    _inherit = 'rating.rating'

    # Adding information for comment a rating message
    publisher_comment = fields.Text("Publisher comment")
    publisher_id = fields.Many2one('res.partner', 'Commented by',
                                   ondelete='set null', readonly=True)
    publisher_datetime = fields.Datetime("Commented on", readonly=True)

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            self._synchronize_publisher_values(values)
        return super().create(values_list)

    def write(self, values):
        self._synchronize_publisher_values(values)
        return super().write(values)

    def _synchronize_publisher_values(self, values):
        """ Force publisher partner and date if not given in order to have
        coherent values. Those fields are readonly as they are not meant
        to be modified manually, behaving like a tracking. """
        if values.get('publisher_comment'):
            if not self.env.user.has_group("website.group_website_restricted_editor"):
                raise exceptions.AccessError(_("Only the publisher of the website can change the rating comment"))
            if not values.get('publisher_datetime'):
                values['publisher_datetime'] = fields.Datetime.now()
            if not values.get('publisher_id'):
                values['publisher_id'] = self.env.user.partner_id.id
        return values
