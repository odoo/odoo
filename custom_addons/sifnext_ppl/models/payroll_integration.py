from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CustomPayrollBatch(models.Model):
    _inherit = 'custom.payroll.batch'

    ppl_id = fields.Many2one('sifnext.ppl', string='PPL Document', readonly=True, copy=False)

    def action_create_ppl(self):
        for batch in self:
            if batch.status != 'approved':
                raise UserError(_("Hanya batch payroll yang disetujui yang dapat dibuatkan PPL."))
            if batch.ppl_id:
                raise UserError(_("Batch payroll ini sudah memiliki PPL."))

            # Hitung total gaji bersih dari semua slip (Take Home Pay)
            total_net = sum(slip.total_pendapatan for slip in batch.slip_ids)
            
            if total_net <= 0:
                raise UserError(_("Total gaji bersih untuk batch ini adalah 0 atau negatif. Tidak dapat membuat PPL."))

            # Buat dokumen PPL
            ppl_vals = {
                'title': f"Pembayaran Gaji - {batch.name}",
                'source_type': 'pegawai',
                'description': f"Tagihan Gaji untuk batch: {batch.name}",
                'line_ids': [(0, 0, {
                    'description': f"Total Gaji Bersih {batch.name}",
                    'quantity': 1,
                    'unit_price': total_net,
                    # journal_account_id idealnya diisi akun 'Beban Gaji', tapi user bisa pilih nanti
                })]
            }
            ppl = self.env['sifnext.ppl'].sudo().create(ppl_vals)
            batch.ppl_id = ppl.id

    def action_view_ppl(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PPL Gaji',
            'res_model': 'sifnext.ppl',
            'res_id': self.ppl_id.id,
            'view_mode': 'form',
        }
