from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CustomPayrollBatch(models.Model):
    _inherit = 'custom.payroll.batch'

    ppl_id = fields.Many2one('sifnext.ppl', string='PPL Document', readonly=True, copy=False)
    ppl_ids = fields.One2many(
        'sifnext.ppl',
        'payroll_batch_id',
        string='PPL per Departemen',
        readonly=True,
    )

    def action_create_ppl(self):
        for batch in self:
            if batch.status != 'approved':
                raise UserError(_("Hanya batch payroll yang disetujui yang dapat dibuatkan PPL."))
            if batch.ppl_id or batch.ppl_ids:
                raise UserError(_("Batch payroll ini sudah memiliki PPL."))

            slips_by_department = {}
            for slip in batch.slip_ids:
                slip_data = slip.sudo()
                employee = slip_data.employee_id
                if slip_data.total_pendapatan <= 0:
                    continue
                department = employee.department_id
                if not department:
                    department = self.env["hr.department"].search([
                        ("company_id", "=", batch.company_id.id),
                        ("name", "=", "Belum Diklasifikasikan"),
                    ], limit=1)
                    if not department:
                        department = self.env["hr.department"].create({
                            "name": "Belum Diklasifikasikan",
                            "company_id": batch.company_id.id,
                            "sif_journal_unit_dept": "pusat",
                        })
                if department.company_id != batch.company_id:
                    raise UserError(_(
                        "Departemen pegawai %(employee)s tidak berasal dari perusahaan/cabang payroll."
                    ) % {"employee": employee.name})
                slips_by_department.setdefault(department.id, self.env["custom.payroll.slip"])
                slips_by_department[department.id] |= slip_data

            if not slips_by_department:
                raise UserError(_("Tidak ada slip gaji dengan nilai lebih dari 0 untuk dibuatkan PPL."))

            created_ppls = self.env["sifnext.ppl"]
            for department_id, slips in slips_by_department.items():
                department = self.env["hr.department"].browse(department_id)
                ppl_lines = [(0, 0, {
                        'description': f"Gaji {slip.employee_id.name}",
                        'employee_id': slip.employee_id.id,
                        'slip_id': slip.id,
                        'quantity': 1,
                        'unit_price': slip.total_pendapatan,
                    }) for slip in slips]
                ppl_vals = {
                    'title': f"Pembayaran Gaji - {batch.name} - {department.name}",
                    'source_type': 'payroll',
                    'applicant_id': batch.submitter_id.id or self.env.user.id,
                    'company_id': batch.company_id.id,
                    'department_id': department.id,
                    'payroll_batch_id': batch.id,
                    'description': f"Tagihan Gaji untuk batch: {batch.name} - {department.name}",
                    'line_ids': ppl_lines,
                }
                ppl = self.env['sifnext.ppl'].with_context(
                    ppl_payroll_integration=True,
                ).sudo().create(ppl_vals)
                created_ppls |= ppl

            batch.ppl_id = created_ppls[:1].id

    def action_view_ppl(self):
        self.ensure_one()
        ppls = self.ppl_ids or self.ppl_id
        if len(ppls) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'PPL Payroll',
                'res_model': 'sifnext.ppl',
                'res_id': ppls.id,
                'view_mode': 'form',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'PPL Payroll per Departemen',
            'res_model': 'sifnext.ppl',
            'view_mode': 'list,form',
            'domain': [('id', 'in', ppls.ids)],
        }
