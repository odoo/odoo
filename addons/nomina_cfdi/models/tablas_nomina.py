# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class TablasAntiguedadesLine(models.Model):
    _name = 'tablas.antiguedades.line'

    form_id = fields.Many2one('tablas.cfdi', string='Vacaciones y aguinaldos', required=True)
    antiguedad = fields.Float('Antigüedad/Años') 
    vacaciones = fields.Float('Vacaciones/Días') 
    prima_vac = fields.Float('Prima vacacional (%)')
    aguinaldo = fields.Float('Aguinaldo/Días')

class TablasGeneralLine(models.Model):
    _name = 'tablas.general.line'

    form_id = fields.Many2one('tablas.cfdi', string='ISR Mensual Art. 113 LISR', required=True)
    lim_inf = fields.Float('Límite inferior') 
    c_fija = fields.Float('Cuota fija') 
    s_excedente = fields.Float('Sobre excedente (%)')

class TablasSubsidiolLine(models.Model):
    _name = 'tablas.subsidio.line'

    form_id = fields.Many2one('tablas.cfdi', string='Subem mensual/CAS Mensual', required=True)
    lim_inf = fields.Float('Límite inferior') 
    s_mensual = fields.Float('Subsidio mensual')

class TablasSubsidio2lLine(models.Model):
    _name = 'tablas.subsidio2.line'

    form_id = fields.Many2one('tablas.cfdi', string='Subsidio Mensual Art. 114 LISR', required=True)
    lim_inf = fields.Float('Límite inferior') 
    c_fija = fields.Float('Cuota fija') 
    s_imp_marginal = fields.Float('Sobre imp. marginal (%)')

class TablasSubsidioAcreditablelLine(models.Model):
    _name = 'tablas.subsidioacreditable.line'

    form_id = fields.Many2one('tablas.cfdi', string='Subsidio acreditable', required=True)
    ano = fields.Float('Año') 
    s_mensual = fields.Float('Subsidio (%)')

class TablasPeriodoBimestrallLine(models.Model):
    _name = 'tablas.periodo.bimestral'

    form_id = fields.Many2one('tablas.cfdi', string='Periodo bimestral', required=True)
    dia_inicio = fields.Date('Primer día del peridoo') 
    dia_fin = fields.Date('Ultímo día del peridoo') 
    no_dias = fields.Float('Dias en el periodo', store=True)

    @api.multi
    @api.onchange('dia_inicio', 'dia_fin')
    def compute_dias(self):
        if self.dia_fin and self.dia_inicio:
           delta = self.dia_fin - self.dia_inicio
           self.no_dias = delta.days + 1

class TablasPeriodoMensuallLine(models.Model):
    _name = 'tablas.periodo.mensual'

    form_id = fields.Many2one('tablas.cfdi', string='Periodo mensual', required=True)
    dia_inicio = fields.Date('Primer día del peridoo') 
    dia_fin = fields.Date('Ultímo día del peridoo') 
    mes = fields.Selection(
        selection=[('01', 'Enero'), 
                   ('02', 'Febrero'), 
                   ('03', 'Marzo'),
                   ('04', 'Abril'), 
                   ('05', 'Mayo'),
                   ('06', 'Junio'),
                   ('07', 'Julio'),
                   ('08', 'Agosto'),
                   ('09', 'Septiembre'),
                   ('10', 'Octubre'),
                   ('11', 'Noviembre'),
                   ('12', 'Diciembre'),
                   ],
        string=_('Mes'),)
    no_dias = fields.Float('Dias en el mes', store=True) 
    @api.multi
    @api.onchange('dia_inicio', 'dia_fin')
    def compute_dias(self):
        if self.dia_fin and self.dia_inicio:
           delta = self.dia_fin - self.dia_inicio
           self.no_dias = delta.days + 1

class TablasPeriodoSemanalLine(models.Model):
    _name = 'tablas.periodo.semanal'

    form_id = fields.Many2one('tablas.cfdi', string='Calendario semanal', required=True)
    no_periodo = fields.Integer('No. periodo')
    dia_inicio = fields.Date('Primer día del peridoo') 
    dia_fin = fields.Date('Ultímo día del peridoo') 
    no_dias = fields.Float('Dias en el periodo', store=True)

    @api.multi
    @api.onchange('dia_inicio', 'dia_fin')
    def compute_dias(self):
        if self.dia_fin and self.dia_inicio:
           delta = self.dia_fin - self.dia_inicio
           self.no_dias = delta.days + 1


class TablasAnualISR(models.Model):
    _name = 'tablas.isr.anual'

    form_id = fields.Many2one('tablas.cfdi', string='ISR Anual', required=True)
    lim_inf = fields.Float('Límite inferior') 
    c_fija = fields.Float('Cuota fija') 
    s_excedente = fields.Float('Sobre excedente (%)')


class TablasCFDI(models.Model):
    _name = 'tablas.cfdi'
    
    name = fields.Char("Nombre")
    tabla_antiguedades = fields.One2many('tablas.antiguedades.line', 'form_id') 
    tabla_LISR = fields.One2many('tablas.general.line', 'form_id')
    tabla_ISR_anual = fields.One2many('tablas.isr.anual', 'form_id')
    tabla_subem = fields.One2many('tablas.subsidio.line', 'form_id')
    tabla_subsidio = fields.One2many('tablas.subsidio2.line', 'form_id')
    tabla_subsidio_acreditable = fields.One2many('tablas.subsidioacreditable.line', 'form_id')
    tabla_bimestral = fields.One2many('tablas.periodo.bimestral', 'form_id')
    tabla_mensual = fields.One2many('tablas.periodo.mensual', 'form_id')
    tabla_semanal = fields.One2many('tablas.periodo.semanal', 'form_id')

    uma = fields.Float(string=_('UMA'), default='84.49')
    salario_minimo = fields.Float(string=_('Salario mínimo'))
    imss_mes = fields.Float('Periodo Mensual para IMSS (dias)',default='30.4')
	
    ex_vale_despensa= fields.Float(string=_('Vale de despena'), compute='_compute_ex_vale_despensa')
    ex_prima_vacacional = fields.Float(string=_('Prima vacacional'), compute='_compute_ex_prima_vacacional')
    ex_aguinaldo = fields.Float(string=_('Aguinaldo'), compute='_compute_ex_aguinaldo')
    ex_fondo_ahorro = fields.Float(string=_('Fondo de ahorro'), compute='_compute_ex_fondo_ahorro')
    ex_tiempo_extra = fields.Float(string=_('Tiempo extra'), compute='_compute_ex_tiempo_extra')
    ex_prima_dominical = fields.Float(string=_('Prima dominical'), compute='_compute_ex_prima_dominical')
    factor_vale_despensa= fields.Float(string=_('Vale de despensa (UMA)'),  default=1)
    factor_prima_vacacional = fields.Float(string=_('Prima vacacional (UMA)'),  default=15)
    factor_aguinaldo = fields.Float(string=_('Aguinaldo (UMA)'),  default=30)
    factor_fondo_ahorro = fields.Float(string=_('Fondo de ahorro (UMA)'), default=1.3)
    factor_tiempo_extra = fields.Float(string=_('Tiempo extra (UMA)'), default=5)
    factor_prima_dominical = fields.Float(string=_('Prima dominical (UMA)'), default=1)
    ex_liquidacion = fields.Float(string=_('Liquidación'), compute='_compute_ex_liquidacion')
    factor_liquidacion = fields.Float(string=_('Liquidación (UMA)'),  default=90)
    ex_ptu = fields.Float(string=_('PTU'), compute='_compute_ex_ptu')
    factor_ptu = fields.Float(string=_('PTU (UMA)'),  default=15)

    importe_utilidades = fields.Float(string=_('Importe a repartir a todos los empleados'), default=0)
    dias_min_trabajados = fields.Float(string=_('Dias mínimos trabajados en empleados eventuales'), default=60)
    funcion_ingresos = fields.Float(string=_('% a repartir en función de los ingresos'), default=50)
    funcion_dias = fields.Float(string=_('% a repartir en función de los días trabajados'), compute='_compute_funcion_dias', readonly=True)
    total_dias_trabajados = fields.Float(string=_('Total de días trabajados'), default=0)
    total_sueldo_percibido = fields.Float(string=_('Total de sueldo percibido'), default=0)
    factor_dias = fields.Float(string=_('Factor por dias trabajados'), compute='_factor_dias', readonly=True)
    factor_sueldo = fields.Float(string=_('Factor por sueldo percibido'), compute='_factor_sueldo', readonly=True)
    fecha_inicio = fields.Date('Fecha inicio')
    fecha_fin = fields.Date('Fecha fin')

    ######## Variables del seguro ####################3
    apotacion_infonavit = fields.Float(string=_('Aportación al Infonavit (%)'), default=5)
    umi = fields.Float(string=_('UMI (Unidad Mixta INFONAVIT)'), default=82.22)
    sbcm_general = fields.Float(string=_('General (UMA)'), default=25)
    sbcm_inv_inf = fields.Float(string=_('Para invalidez e Infonavit (UMA)'), default=25)
    rt_prom_vida_activa = fields.Float(string=_('Promedio de vida activa (años)'), default=28)
    rt_prom_vida_fprima = fields.Float(string=_('Factor de prima'), default=2.3)
    rt_prom_vida_pmin = fields.Float(string=_('Prima mínima (%)'), default=0.5)
    rt_prom_vida_pmax = fields.Float(string=_('Prima máxima (%)'), default=15)
    rt_prom_vida_varmax = fields.Float(string=_('Variación máxima de prima (%)'), default=1)
    enf_mat_cuota_fija = fields.Float(string=_('Cuota fija (%)'), default=20.4)
    enf_mat_excedente_p = fields.Float(string=_('Excedente de 3 UMA (%)'), default=1.10)
    enf_mat_excedente_e = fields.Float(string=_('Excedente de 3 UMA (%)'), default=0.40)

    enf_mat_prestaciones_p = fields.Float(string=_('Prestaciones en dinero (%)'), default=0.7)
    enf_mat_prestaciones_e = fields.Float(string=_('Prestaciones en dinero (%)'), default=0.25)
    enf_mat_gastos_med_p = fields.Float(string=_('Gastos médicos personales (%)'), default=1.5)
    enf_mat_gastos_med_e = fields.Float(string=_('Gastos médicos personales (%)'), default=0.375)

    inv_vida_p = fields.Float(string=_('Invalidez y vida (%)'), default=1.75)
    inv_vida_e = fields.Float(string=_('Invalidez y vida (%)'), default=0.625)

    cesantia_vejez_p = fields.Float(string=_('Cesantía y vejez (%)'), default=3.15)
    cesantia_vejez_e = fields.Float(string=_('Cesantía y vejez (%)'), default=1.125)

    retiro_p = fields.Float(string=_('Retiro (%)'), default=2)
    guarderia_p = fields.Float(string=_('Guardería y prestaciones sociales (%)'), default=1)

    @api.one
    @api.constrains('name')
    def _check_name(self):
        if self.name:
            if self.search([('id', '!=', self.id),('name','=',self.name)]):
                raise ValidationError(_('Reference with same name already exist.'))
            
    @api.model
    def default_get(self,fields):
        res = super(TablasCFDI,self).default_get(fields)
        if 'name' in fields:
            res['name'] = self.env['ir.sequence'].next_by_code('tablas.cfdi.reference')
        return res

    @api.one
    @api.depends('funcion_ingresos')
    def _compute_funcion_dias(self):
        self.funcion_dias = 100 - self.funcion_ingresos

    @api.one
    @api.depends('total_dias_trabajados', 'total_sueldo_percibido')
    def _factor_dias(self):
        if self.total_dias_trabajados > 0:
            self.factor_dias = (self.importe_utilidades*(self.funcion_dias/100)) / self.total_dias_trabajados

    @api.one
    @api.depends('total_dias_trabajados', 'total_sueldo_percibido')
    def _factor_sueldo(self):
        if self.total_sueldo_percibido > 0:
            self.factor_sueldo = (self.importe_utilidades*(self.funcion_ingresos/100)) / self.total_sueldo_percibido

    @api.one
    @api.depends('uma')
    def _compute_ex_vale_despensa(self):
        self.ex_vale_despensa = self.uma * self.imss_mes * self.factor_vale_despensa

    @api.one
    @api.depends('uma')
    def _compute_ex_prima_dominical(self):
        self.ex_prima_dominical = self.uma * self.factor_prima_dominical

    @api.one
    @api.depends('uma')
    def _compute_ex_fondo_ahorro(self):
        self.ex_fondo_ahorro = self.uma * self.imss_mes * self.factor_fondo_ahorro

    @api.one
    @api.depends('uma')
    def _compute_ex_prima_vacacional(self):
        self.ex_prima_vacacional = self.uma * self.factor_prima_vacacional 

    @api.one
    @api.depends('uma')
    def _compute_ex_aguinaldo(self):
        self.ex_aguinaldo = self.uma * self.factor_aguinaldo

    @api.one
    @api.depends('uma')
    def _compute_ex_tiempo_extra(self):
        self.ex_tiempo_extra = self.uma * self.factor_tiempo_extra

    @api.one
    @api.depends('uma')
    def _compute_ex_liquidacion(self):
        self.ex_liquidacion = self.uma * self.factor_liquidacion

    @api.one
    @api.depends('uma')
    def _compute_ex_ptu(self):
        self.ex_ptu = self.uma * self.factor_ptu

    def calcular_reparto_utilidades(self):
        payslips = self.env['hr.payslip'].search([('date_from', '>=', self.fecha_inicio), ('date_to', '<=', self.fecha_fin),('tipo_nomina','=', 'O')])
        work100_lines = payslips.mapped('worked_days_line_ids').filtered(lambda x:x.code=='WORK100')
        net_lines = payslips.mapped('line_ids').filtered(lambda x:x.code=='NET')
        
        total_dias_trabajados, total_sueldo_percibido = 0.0, 0.0
        
        total_dias_by_employee = {}
        total_sueldo_employee = {}
        for line in work100_lines:
            total_dias_trabajados += line.number_of_days
            if line.payslip_id.employee_id not in total_dias_by_employee:
                total_dias_by_employee.update({line.payslip_id.employee_id: 0.0})
            total_dias_by_employee[line.payslip_id.employee_id] += line.number_of_days
            
        for line in net_lines:
            total_sueldo_percibido += line.total
            if line.slip_id.employee_id not in total_sueldo_employee:
                total_sueldo_employee.update({line.slip_id.employee_id: 0.0})
            total_sueldo_employee[line.slip_id.employee_id] += line.total
        
        employees = list(set(list(total_dias_by_employee.keys())  + list(total_sueldo_employee.keys())))
        for employee in employees:
            employee.write({'dias_utilidad' : total_dias_by_employee.get(employee, 0.0), 'sueldo_utilidad' : total_sueldo_employee.get(employee,0.0)})
            
        self.write({'total_dias_trabajados': total_dias_trabajados, 'total_sueldo_percibido':total_sueldo_percibido})
        
        return True

    @api.multi
    def button_dummy(self):
        self.calcular_reparto_utilidades()
        return True