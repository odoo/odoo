# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import AccessError, UserError


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    show_send_without_mail = fields.Boolean(string="Show Send Only", compute='_compute_show_send_without_mail')

    @api.depends('model')
    def _compute_show_send_without_mail(self):
        show = False
        if self.model in ['sale.order', 'purchase.order']:
            order = self.env[self.model].browse(self.res_id)
            if order and order.state == 'sent':
                show = False
            elif self.env.context.get('send_rfq') or self.env.context.get('mark_so_as_sent'):
                show = True
        self.show_send_without_mail = show
        
    def action_send_without_mail(self):
        # hook
        if self.model in ['sale.order', 'purchase.order']:
            pass
        else:
            raise UserError(_('This only available in Sale Order or Purchase Order'))
        return {'type': 'ir.actions.act_window_close'}
