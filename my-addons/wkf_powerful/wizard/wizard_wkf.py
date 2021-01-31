# -*- coding: utf-8 -*-
##############################################################################

from odoo import api, fields, models, _


class wizard_wkf_message(models.TransientModel):
    _name = 'wizard.wkf.message'
    _description = 'Wkf Message'
    name = fields.Char(u'Note')


    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        order = self.env[ctx.get('active_model')].browse(ctx.get('active_id'))
        order.with_context(ctx).wkf_action(self.name)
        return True





