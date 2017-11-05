# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.calendar.models.calendar import get_real_ids


class MailInvite(models.TransientModel):

    _inherit = 'mail.wizard.invite'

    @api.model
    def default_get(self, fields):
        """ In case someone clicked on 'invite others' wizard in the followers widget, transform virtual ids in real ids """
        if 'default_res_id' in self._context:
            self = self.with_context(default_res_id=get_real_ids(self._context['default_res_id']))

        result = super(MailInvite, self).default_get(fields)
        if 'res_id' in result:
            result['res_id'] = get_real_ids(result['res_id'])
        return result
