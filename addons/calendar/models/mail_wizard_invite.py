# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from ..models.calendar import get_real_ids


class InviteWizard(models.TransientModel):
    _inherit = 'mail.wizard.invite'

    @api.model
    def default_get(self, fields):
        '''
        in case someone clicked on 'invite others' wizard in the followers widget, transform virtual ids in real ids
        '''
        context = self.env.context
        if 'default_res_id' in context:
            context = dict(context, default_res_id=get_real_ids(context['default_res_id']))
        result = super(InviteWizard, self.with_context(context)).default_get(fields)
        if 'res_id' in result:
            result['res_id'] = get_real_ids(result['res_id'])
        return result
