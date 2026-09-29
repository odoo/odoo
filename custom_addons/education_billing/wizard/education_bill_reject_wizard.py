# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import html_escape


class EducationBillRejectWizard(models.TransientModel):
    _name = 'education.bill.reject.wizard'
    _description = 'Wizard Penolakan Verifikasi Pembayaran'

    bill_id = fields.Many2one(
        'education.bill',
        string='Tagihan Terkait',
        required=True
    )
    reason = fields.Text(
        string='Alasan Penolakan Bukti Bayar',
        required=True,
        help='Jelaskan alasan penolakan, misal: bukti transfer buram, nominal tidak sesuai, rekening tujuan salah, dsb.'
    )

    def action_confirm_reject(self):
        self.ensure_one()
        bill = self.bill_id
        if bill.state not in ('waiting_verification', 'unpaid'):
            raise UserError(_('Tagihan ini tidak dalam status yang dapat ditolak.'))

        bill.write({
            'state': 'rejected',
            'reject_reason': self.reason,
            'verified_by_id': False,
            'verified_date': False,
        })
        bill.message_post(
            body="<b>%s</b><br/>%s %s" % (
                html_escape(_('Verifikasi Pembayaran Ditolak oleh %s') % self.env.user.name),
                html_escape(_('Alasan:')),
                html_escape(self.reason or ''),
            )
        )
        return {'type': 'ir.actions.act_window_close'}
