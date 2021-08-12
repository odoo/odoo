# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
#from odoo.addons.hr_payroll.wizard.hr_payroll_payslips_by_employees import HrPayslipEmployees
from datetime import datetime

class HrPayslipEmployeesExt(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    
    @api.multi
    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        payslip_batch = self.env['hr.payslip.run'].browse(active_id)
        struct_id = payslip_batch.estructura and payslip_batch.estructura.id or False
        other_inputs = []
        for other in payslip_batch.tabla_otras_entradas:
            if other.descripcion and other.codigo: 
                other_inputs.append((0,0,{'name':other.descripcion, 'code': other.codigo, 'amount':other.monto}))
            
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': struct_id or slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
                #Added
                'tipo_nomina' : payslip_batch.tipo_nomina,
                
            }
            if other_inputs and res.get('contract_id'):
                contract_id = res.get('contract_id')
                input_lines = list(other_inputs)
                for line in input_lines:
                    line[2].update({'contract_id':contract_id})
                #input_lines = map(lambda x: x[2].update({'contract_id':contract_id}),input_lines)
                res.update({'input_line_ids': input_lines,})
            res.update({'dias_pagar': payslip_batch.dias_pagar,
                            'imss_dias': payslip_batch.imss_dias,
                            'imss_mes': payslip_batch.imss_mes,
                            'no_nomina': payslip_batch.no_nomina,
                            'mes': '{:02d}'.format(datetime.strptime(to_date,"%Y-%m-%d").month),
                            'isr_devolver': payslip_batch.isr_devolver,
                            'isr_ajustar': payslip_batch.isr_ajustar,
                            'concepto_periodico': payslip_batch.concepto_periodico})

            payslips += self.env['hr.payslip'].create(res)
            
        payslips.compute_sheet()
        
        return {'type': 'ir.actions.act_window_close'}
    
#     @api.multi
#     def compute_sheet(self):
#         res = super(HrPayslipEmployees, self).compute_sheet()
#         active_id = self.env.context.get('active_id')
#         if active_id and self.employee_ids:
#             payslips = self.env['hr.payslip'].search([('employee_id', '=', self.employee_ids.ids), ('payslip_run_id', '=', active_id)])
#             payslip_batch = self.env['hr.payslip.run'].browse(active_id)
#             payslips.write({'tipo_nomina': payslip_batch.tipo_nomina})
#         return res
    
        
#HrPayslipEmployees.compute_sheet = HrPayslipEmployeesExt.compute_sheet
