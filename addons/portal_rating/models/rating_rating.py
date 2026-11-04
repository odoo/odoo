# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _


class Rating(models.Model):
    _inherit = 'rating.rating'

    # Adding information for comment a rating message
    publisher_comment = fields.Text("Publisher comment")
    publisher_id = fields.Many2one('res.partner', 'Commented by',
                                   ondelete='set null', readonly=True,
                                   index='btree_not_null')
    publisher_datetime = fields.Datetime("Commented on", readonly=True)

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            self._synchronize_publisher_values(values)
        ratings = super().create(values_list)
        if any(rating.publisher_comment for rating in ratings):
            ratings._check_synchronize_publisher_values()
        return ratings

    def write(self, values):
        self._synchronize_publisher_values(values)
        return super().write(values)

    def _check_synchronize_publisher_values(self):
        """ Either current user is a member of website restricted editor group
        (done here by fetching the group record then using has_group, as it may
        not be defined and we do not want to make a complete bridge module just
        for that). Either write access on document is granted. """
        editor_group = self.env['ir.model.data']._xmlid_to_res_id('website.group_website_restricted_editor')
        if editor_group and self.env.user.has_group('website.group_website_restricted_editor'):
            return
        for model, model_data in self._classify_by_model().items():
            records = self.env[model].browse(model_data['record_ids'])
            try:
                records.check_access('write')
            except exceptions.AccessError as e:
                raise exceptions.AccessError(
                    _("Updating rating comment require write access on related record")
                ) from e

    def _synchronize_publisher_values(self, values):
        """ Force publisher partner and date if not given in order to have
        coherent values. Those fields are readonly as they are not meant
        to be modified manually, behaving like a tracking. """
        if values.get('publisher_comment'):
            self._check_synchronize_publisher_values()
            if not values.get('publisher_datetime'):
                values['publisher_datetime'] = fields.Datetime.now()
            if not values.get('publisher_id'):
                values['publisher_id'] = self.env.user.partner_id.id
        return values
