# -*- coding: utf-8 -*-

from odoo import models, api, fields
from datetime import datetime
from datetime import date

import time
from odoo.exceptions import Warning

class GeneraLiquidaciones(models.TransientModel):
    _name = 'calculo.liquidaciones'

    fecha_inicio = fields.Date(string='Fecha ultimo periodo nómina')
    fecha_liquidacion = fields.Date(string='Fecha liquidacion')
    employee_id =fields.Many2one("hr.employee",'Employee')
    dias_base = fields.Float('Días base', default='90')
    dias_x_ano = fields.Float('Días por cada año trabajado', default='20')
    dias_totales = fields.Float('Total de días', store=True)
    indemnizacion = fields.Boolean("Indemnizar al empleado")
    dias_pendientes_pagar = fields.Float('Días a pagar', store=True)
    dias_vacaciones = fields.Integer('Días de vacaciones')
    dias_aguinaldo = fields.Integer('Días aguinaldo')
    fondo_ahorro = fields.Float('Fondo ahorro', compute="get_fondo_ahorro", store=True)
    prima_vacacional = fields.Boolean("Prima vacacional pendiente")
    pago_separacion = fields.Float("Pago por separación")
    contract_id = fields.Many2one('hr.contract', string='Contrato')
    antiguedad_anos = fields.Float('Antiguedad', store=True)

    monto_prima_antiguedad = fields.Float('Prima antiguedad',readonly=True, store=True)
    monto_indemnizacion = fields.Float('Indemnizacion',readonly=True, store=True)
    @api.multi
    def calculo_create(self):
        employee = self.employee_id
        if not employee:
            raise Warning("Seleccione primero al empleado.")
        payslip_batch_nm = 'Liquidacion ' +employee.name
        date_from = self.fecha_inicio
        date_to = self.fecha_liquidacion
        batch = self.env['hr.payslip.run'].create({
            'name' : payslip_batch_nm,
            'date_start': date_from,
            'date_end': date_to,
            'periodicidad_pago': '04',
            'no_nomina': '1',
            })
        batch
        payslip_obj = self.env['hr.payslip']
        payslip_onchange_vals = payslip_obj.onchange_employee_id(date_from, date_to, employee_id=employee.id)
        payslip_vals = {**payslip_onchange_vals.get('value',{})} #TO copy dict to new dict. 
        
        structure = self.env['hr.payroll.structure'].search([('name','=','Liquidación - Ordinario')], limit=1)
        if structure: 
            payslip_vals['struct_id'] = structure.id
        
        contract_id = self.contract_id.id
        if not contract_id:
            contract_id = payslip_vals.get('contract_id')
        else:
            payslip_vals['contract_id'] = contract_id 
        
        if not contract_id:
            contract_id = employee.contract_id.id
        if not contract_id:
            raise Warning("No se encontró contrato para %s en el periodo de tiempo."%(employee.name))
        
        worked_days = []
        worked_days.append((0,0,{'name' :'Dias a pagar', 'code' : 'WORK100', 'contract_id':contract_id, 'number_of_days': self.dias_pendientes_pagar}))
        worked_days.append((0,0,{'name' :'Dias aguinaldo', 'code' : 'AGUI', 'contract_id':contract_id, 'number_of_days': self.dias_aguinaldo}))
        worked_days.append((0,0,{'name' :'Dias vacaciones', 'code' : 'VAC', 'contract_id':contract_id, 'number_of_days': self.dias_vacaciones}))
        
        payslip_vals['input_line_ids']=[(0,0, {'name':'Fondo ahorro', 'code': 'PFA', 'amount': self.fondo_ahorro, 'contract_id':contract_id})]
        
        payslip_vals.update({
            'employee_id' : employee.id,
            'worked_days_line_ids' : worked_days,
            'tipo_nomina' : 'O',
            'payslip_run_id' : batch.id,
            'date_from': date_from,
            'date_to': date_to,
            #'input_line_ids': [(0, 0, x) for x in payslip_vals.get('input_line_ids',[])],
            #'mes': datetime.strptime(date_to, '%Y-%m-%d').month
            })
        payslip_obj.create(payslip_vals)
        
        payslip_vals2 = {**payslip_onchange_vals.get('value',{})}
        structure = self.env['hr.payroll.structure'].search([('name','=','Liquidación - indemnizacion/finiquito')], limit=1)
        if structure: 
            payslip_vals2['struct_id'] = structure.id
        
        other_inputs = []
        other_inputs.append((0,0,{'name' :'Prima antiguedad', 'code' : 'PDA', 'contract_id':contract_id, 'amount': self.monto_prima_antiguedad}))
        other_inputs.append((0,0,{'name' :'Indemnizacion', 'code' : 'IND', 'contract_id':contract_id, 'amount': self.monto_indemnizacion}))
        other_inputs.append((0,0,{'name' :'Pago por separacion', 'code' : 'PPS', 'contract_id':contract_id, 'amount': self.pago_separacion}))
        worked_days2 = []
        worked_days2.append((0,0,{'name' :'Dias a pagar', 'code' : 'WORK100', 'contract_id':contract_id, 'number_of_days': 0}))

        payslip_vals2.update({
            'employee_id' : employee.id,
            'tipo_nomina' : 'E',
            'input_line_ids' : other_inputs,
            'payslip_run_id' : batch.id,
            'date_from': date_from,
            'date_to': date_to,
            'contract_id' : contract_id,
            'fecha_pago' : date_to,
            'worked_days_line_ids': worked_days2, #[(0, 0, x) for x in payslip_vals2.get('worked_days_line_ids',[])],
            })
        payslip_obj.create(payslip_vals2)
            
        return
    
    @api.multi
    def calculo_liquidacion(self):
        if self.employee_id and self.contract_id:
            #cálculo de conceptos de nómina extraordinaria
            self.antiguedad_anos = self.contract_id.antiguedad_anos
            #calculo de dias a indemnizar
            if self.indemnizacion:
                self.dias_totales = self.contract_id.antiguedad_anos * self.dias_x_ano + self.dias_base
            else:
                self.dias_totales = 0
            self.monto_indemnizacion = self.dias_totales * self.contract_id.sueldo_diario

            # calculo prima antiguedad: 12 días de salario por cada año de servicio.
            self.monto_prima_antiguedad = self.contract_id.antiguedad_anos * 12 * self.contract_id.sueldo_diario

            #cálculo de conceptos de nómina ordinaria
            #dias pendientes a pagar en ultima nomina
            delta_dias  = self.fecha_liquidacion - self.fecha_inicio
            self.dias_pendientes_pagar = delta_dias.days + 1

            #Dias de aguinaldo
            year_date_start = self.contract_id.date_start.year
            first_day_date = datetime(date.today().year, 1, 1)
            if year_date_start < date.today().year:
                delta1 = self.fecha_liquidacion - first_day_date
                self.dias_aguinaldo = delta1.days
            else:
                delta2 = self.fecha_liquidacion - self.contract_id.date_start
                self.dias_aguinaldo = delta2.days

            #dias de vacaciones
            self.dias_vacaciones = sum([r.dias for r in self.contract_id.tabla_vacaciones])

            #fondo de ahorro (si hay)
            self.fondo_ahorro = self.get_fondo_ahorro()

            #prima vacacional liquidacion
        return {
            "type": "ir.actions.do_nothing",
        }


    @api.multi
    def genera_nominas(self):
        dias_vacaciones = 0

    def get_fondo_ahorro(self):
        total = 0
        if self.employee_id and self.contract_id.tablas_cfdi_id:
            year_date_start = self.contract_id.year
            first_day_date = datetime(date.today().year, 1, 1)
            if year_date_start < date.today().year:
                date_start = first_day_date
            else:
                date_start = self.contract_id.date_start
            date_end = self.fecha_liquidacion

            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'D067')])
            payslips = self.env['hr.payslip'].search(domain)
            payslip_lines = payslips.mapped('line_ids').filtered(lambda x: x.salary_rule_id.id in rules.ids)
            employees = {}
            for line in payslip_lines:
                if line.slip_id.employee_id not in employees:
                    employees[line.slip_id.employee_id] = {line.slip_id: []}
                if line.slip_id not in employees[line.slip_id.employee_id]:
                    employees[line.slip_id.employee_id].update({line.slip_id: []})
                employees[line.slip_id.employee_id][line.slip_id].append(line)

            for employee, payslips in employees.items():
                for payslip,lines in payslips.items():
                    for line in lines:
                        total += line.total
        return total
