# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Rating(models.Model):

    _inherit = "rating.rating"

    @api.one
    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        # cannot change the rec_name of session since it is use to create the bus channel
        # so, need to override this method to set the same alternative rec_name as in reporting
        if self.res_model == 'mail.channel':
            current_object = self.env[self.res_model].sudo().browse(self.res_id)
            self.res_name = ('%s / %s') % (current_object.livechat_channel_id.name, current_object.id)
        else:
            super(Rating, self)._compute_res_name()
