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

            # Buat baris PPL per pegawai
            ppl_lines = []
            for slip in batch.slip_ids:
                if slip.total_pendapatan > 0:
                    ppl_lines.append((0, 0, {
                        'description': f"Gaji {slip.employee_id.name}",
                        'quantity': 1,
                        'unit_price': slip.total_pendapatan,
                    }))
            
            if not ppl_lines:
                raise UserError(_("Tidak ada slip gaji dengan nilai lebih dari 0 untuk dibuatkan PPL."))

            unit = self.env['sifnext.unit'].search([('company_id', '=', batch.company_id.id)], limit=1)
            # Buat dokumen PPL
            ppl_vals = {
                'title': f"Pembayaran Gaji - {batch.name}",
                'source_type': 'pegawai',
                'unit_id': unit.id if unit else False,
                'description': f"Tagihan Gaji untuk batch: {batch.name}",
                'line_ids': ppl_lines
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
