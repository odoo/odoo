# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EducationBillMassUpdateWizard(models.TransientModel):
    _name = 'education.bill.mass.update.wizard'
    _description = 'Wizard Ubah Status Tagihan Massal'

    bill_ids = fields.Many2many(
        'education.bill',
        string='Tagihan Terpilih',
        default=lambda self: self.env.context.get('active_ids', [])
    )
    total_selected = fields.Integer(
        string='Jumlah Tagihan Terpilih',
        compute='_compute_total_selected'
    )
    target_state = fields.Selection([
        ('unpaid', 'Diajukan / Diterbitkan (Belum Dibayar)'),
        ('waiting_verification', 'Menunggu Verifikasi'),
        ('verified', 'Terverifikasi (Lunas & Auto Jurnal)'),
        ('draft', 'Draft (Konsep)'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status Tujuan', required=True, default='verified')

    payment_method = fields.Selection([
        ('transfer', 'Transfer Bank'),
        ('cash', 'Kasir / Tunai'),
        ('va', 'Virtual Account'),
        ('qris', 'QRIS'),
    ], string='Metode Pembayaran', default='transfer')
    payment_date = fields.Date(
        string='Tanggal Pembayaran',
        default=fields.Date.context_today
    )
    notes = fields.Text(string='Catatan Tambahan')

    @api.depends('bill_ids')
    def _compute_total_selected(self):
        for rec in self:
            rec.total_selected = len(rec.bill_ids)

    def action_apply(self):
        self.ensure_one()
        if not self.bill_ids:
            raise UserError(_('Tidak ada tagihan yang dipilih.'))

        updated_count = 0
        skipped_count = 0

        for bill in self.bill_ids:
            try:
                if self.target_state == 'verified':
                    if bill.state == 'verified':
                        skipped_count += 1
                        continue
                    if bill.state == 'draft':
                        bill.action_publish_bill()
                    if self.payment_method:
                        bill.payment_method = self.payment_method
                    if self.payment_date:
                        bill.payment_date = self.payment_date
                    if self.notes:
                        bill.notes = self.notes
                    bill.action_verify_payment()
                    updated_count += 1

                elif self.target_state == 'waiting_verification':
                    if bill.state == 'waiting_verification':
                        skipped_count += 1
                        continue
                    if bill.state == 'verified':
                        skipped_count += 1
                        continue
                    if bill.state == 'draft':
                        bill.action_publish_bill()
                    bill.write({
                        'state': 'waiting_verification',
                        'payment_date': self.payment_date or fields.Date.context_today(self),
                        'payment_method': self.payment_method or 'transfer',
                        'reject_reason': False,
                    })
                    updated_count += 1

                elif self.target_state == 'unpaid':
                    if bill.state == 'unpaid':
                        skipped_count += 1
                        continue
                    if bill.state == 'verified':
                        skipped_count += 1
                        continue
                    bill.write({
                        'state': 'unpaid',
                        'reject_reason': False,
                    })
                    updated_count += 1

                elif self.target_state == 'draft':
                    if bill.state == 'draft':
                        skipped_count += 1
                        continue
                    if bill.state == 'verified':
                        skipped_count += 1
                        continue
                    bill.write({
                        'state': 'draft',
                        'verified_by_id': False,
                        'verified_date': False,
                        'reject_reason': False,
                    })
                    updated_count += 1

                elif self.target_state == 'cancelled':
                    if bill.state == 'cancelled':
                        skipped_count += 1
                        continue
                    if bill.state == 'verified':
                        skipped_count += 1
                        continue
                    bill.write({'state': 'cancelled'})
                    updated_count += 1

            except Exception:
                skipped_count += 1
                continue

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Update Status Massal Selesai'),
                'message': _('%d tagihan berhasil diubah ke status "%s" (%d dilewati).') % (
                    updated_count,
                    dict(self._fields['target_state'].selection).get(self.target_state),
                    skipped_count
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
