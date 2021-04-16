# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions, fields, models


class MailMessage(models.Model):
    #TODO: documentation
    
    _inherit = 'mail.message'

    def message_format(self):

        message_values = super().message_format()

        rating_id = self.env['ir.model.data'].xmlid_to_res_id('project.mt_task_rating')
        for vals in message_values:
            message_sudo = self.browse(vals['id']).sudo().with_prefetch(self.ids)
            vals.update({
                'is_rating': message_sudo.subtype_id.id == rating_id,
            })
        return message_values
