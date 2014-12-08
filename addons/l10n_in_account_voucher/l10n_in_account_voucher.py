# -*- coding: utf-8 -*-

from openerp import fields, models, api
from openerp.tools import amount_to_text_en


class account_voucher(models.Model):

    _inherit = 'account.voucher'

    amount = fields.Float(track_visibility='onchange')
    partner_id = fields.Many2one(track_visibility='onchange')
    writeoff_acc_id = fields.Many2one(track_visibility='onchange')
    journal_id = fields.Many2one(track_visibility='onchange')
    period_id = fields.Many2one(track_visibility='onchange')

    @api.model
    def convert(self):
        return amount_to_text_en.amount_to_text(self.amount, 'en', self.currency_id.name)

    @api.multi
    def get_invoice_followers(self, move_ids):
        message_follower_ids = []
        move_line = self.env['account.move.line'].search([('id', 'in', move_ids)])
        for line in move_line:
            if line.invoice:
                message_follower_ids = [follower.id for follower in line.invoice.message_follower_ids if follower.id not in message_follower_ids]
        return message_follower_ids

    @api.multi
    def proforma_voucher(self):
        for voucher in self:
            if voucher.type in ('sale', 'receipt'):
                move_ids = [l.move_line_id.id for l in voucher.line_cr_ids]
            elif voucher.type in ('purchase', 'payment'):
                move_ids = [l.move_line_id.id for l in voucher.line_dr_ids]
        self.message_follower_ids = self.get_invoice_followers(move_ids)
        return super(account_voucher, self).proforma_voucher()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
