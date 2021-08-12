# -*- coding: utf-8 -*-

import base64
import json
import requests
from lxml import etree
#import time
import datetime

from datetime import timedelta
from datetime import time as datetime_time
from dateutil import relativedelta
from pytz import timezone

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from reportlab.graphics.barcode import createBarcodeDrawing #, getCodes
from reportlab.lib.units import mm
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF 

class HrSalaryRule(models.Model):
    #_inherit = ['hr.salary.rule','mail.thread']
    _inherit = 'hr.salary.rule'
    tipo_percepcion = fields.Selection(
        selection=[('001', 'Sueldos, Salarios  Rayas y Jornales'), 
                   ('002', 'Gratificación Anual (Aguinaldo)'), 
                   ('003', 'Participación de los Trabajadores en las Utilidades PTU'),
                   ('004', 'Reembolso de Gastos Médicos Dentales y Hospitalarios'), 
                   ('005', 'Fondo de ahorro'),
                   ('006', 'Caja de ahorro'),
                   ('009', 'Contribuciones a Cargo del Trabajador Pagadas por el Patrón'), 
                   ('010', 'Premios por puntualidad'),
                   ('011', 'Prima de Seguro de vida'), 
                   ('012', 'Seguro de Gastos Médicos Mayores'), 
                   ('013', 'Cuotas Sindicales Pagadas por el Patrón'), 
                   ('014', 'Subsidios por incapacidad'),
                   ('015', 'Becas para trabajadores y/o hijos'), 
                   ('019', 'Horas extra'),
                   ('020', 'Prima dominical'), 
                   ('021', 'Prima vacacional'),
                   ('022', 'Prima por antigüedad'),
                   ('023', 'Pagos por separación'),
                   ('024', 'Seguro de retiro'),
                   ('025', 'Indemnizaciones'), 
                   ('026', 'Reembolso por funeral'), 
                   ('027', 'Cuotas de seguridad social pagadas por el patrón'), 
                   ('028', 'Comisiones'),
                   ('029', 'Vales de despensa'),
                   ('030', 'Vales de restaurante'), 
                   ('031', 'Vales de gasolina'),
                   ('032', 'Vales de ropa'), 
                   ('033', 'Ayuda para renta'), 
                   ('034', 'Ayuda para artículos escolares'), 
                   ('035', 'Ayuda para anteojos'),
                   ('036', 'Ayuda para transporte'), 
                   ('037', 'Ayuda para gastos de funeral'),
                   ('038', 'Otros ingresos por salarios'), 
                   ('039', 'Jubilaciones, pensiones o haberes de retiro'),
                   ('044', 'Jubilaciones, pensiones o haberes de retiro en parcialidades'),
                   ('045', 'Ingresos en acciones o títulos valor que representan bienes'),
                   ('046', 'Ingresos asimilados a salarios'),
                   ('047', 'Alimentación'), 
                   ('048', 'Habitación'), 
                   ('049', 'Premios por asistencia'), 
                   ('050', 'Viáticos'),
                   ('051', 'Pagos por gratificaciones, primas, compensaciones, recompensas u otros a extrabajadores derivados de jubilación en parcialidades'),
                   ('052', 'Pagos que se realicen a extrabajadores que obtengan una jubilación en parcialidades derivados de la ejecución de resoluciones judicial o de un laudo'),
                   ('053', 'Pagos que se realicen a extrabajadores que obtengan una jubilación en una sola exhibición derivados de la ejecución de resoluciones judicial o de un laudo'),],
        string=_('Tipo de percepción'),
    )
    tipo_deduccion = fields.Selection(
        selection=[('001', 'Seguridad social'), 
                   ('002', 'ISR'), 
                   ('003', 'Aportaciones a retiro, cesantía en edad avanzada y vejez.'),
                   ('004', 'Otros'), 
                   ('005', 'Aportaciones a Fondo de vivienda'),
                   ('006', 'Descuento por incapacidad'),
                   ('007', 'Pensión alimenticia'),
                   ('008', 'Renta'),
                   ('009', 'Préstamos provenientes del Fondo Nacional de la Vivienda para los Trabajadores'), 
                   ('010', 'Pago por crédito de vivienda'),
                   ('011', 'Pago de abonos INFONACOT'), 
                   ('012', 'Anticipo de salarios'), 
                   ('013', 'Pagos hechos con exceso al trabajador'), 
                   ('014', 'Errores'),
                   ('015', 'Pérdidas'), 
                   ('016', 'Averías'), 
                   ('017', 'Adquisición de artículos producidos por la empresa o establecimiento'),
                   ('018', 'Cuotas para la constitución y fomento de sociedades cooperativas y de cajas de ahorro'), 				   
                   ('019', 'Cuotas sindicales'),
                   ('020', 'Ausencia (Ausentismo)'), 
                   ('021', 'Cuotas obrero patronales'),
                   ('022', 'Impuestos Locales'),
                   ('023', 'Aportaciones voluntarias'),
                   ('080', 'Ajuste en Viáticos gravados'),
                   ('081', 'Ajuste en Viáticos (entregados al trabajador)'),
                   ('101', 'ISR Retenido de ejercicio anterior'),
                   ('102', 'Ajuste a pagos por gratificaciones, primas, compensaciones, recompensas u otros a extrabajadores derivados de jubilación en parcialidades, gravados'),
                   ('103', 'Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en parcialidades derivados de la ejecución de una resolución judicial o de un laudo gravados'),
                   ('104', 'Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en parcialidades derivados de la ejecución de una resolución judicial o de un laudo exentos'),
                   ('105', 'Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en una sola exhibición derivados de la ejecución de una resolución judicial o de un laudo gravados'),
                   ('106', 'Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en una sola exhibición derivados de la ejecución de una resolución judicial o de un laudo exentos'),],
        string=_('Tipo de deducción'),
    )

    tipo_otro_pago = fields.Selection(
        selection=[('001', 'Reintegro de ISR pagado en exceso'), 
                   ('002', 'Subsidio para el empleo'), 
                   ('003', 'Viáticos'),
                   ('004', 'Aplicación de saldo a favor por compensación anual'), 
                   ('005', 'Reintegro de ISR retenido en exceso de ejercicio anterior'),
                   ('999', 'Pagos distintos a los listados y que no deben considerarse como ingreso por sueldos, salarios o ingresos asimilados'),],
        string=_('Otros Pagos'),)
    category_code = fields.Char("Category Code",related="category_id.code",store=True)

    forma_pago = fields.Selection(
        selection=[('001', 'Efectivo'), 
                   ('002', 'Especie'),],
        string=_('Forma de pago'),default='001')

class HrPayslip(models.Model):
    _name = "hr.payslip"
    _inherit = ['hr.payslip','mail.thread']


    tipo_nomina = fields.Selection(
        selection=[('O', 'Nómina ordinaria'), 
                   ('E', 'Nómina extraordinaria'),],
        string=_('Tipo de nómina'), required=True, default='O'
    )

    estado_factura = fields.Selection(
        selection=[('factura_no_generada', 'Factura no generada'), ('factura_correcta', 'Factura correcta'), 
                   ('problemas_factura', 'Problemas con la factura'), ('factura_cancelada', 'Factura cancelada')],
        string=_('Estado de factura'),
        default='factura_no_generada',
        readonly=True
    )	
    imss_dias = fields.Float('Cotizar en el IMSS',default='15') #, readonly=True) 
    imss_mes = fields.Float('Dias a cotizar en el mes',default='30') #, readonly=True)
    xml_nomina_link = fields.Char(string=_('XML link'), readonly=True)
    nomina_cfdi = fields.Boolean('Nomina CFDI')
    qrcode_image = fields.Binary("QRCode")
    qr_value = fields.Char(string=_('QR Code Value'))
    numero_cetificado = fields.Char(string=_('Numero de cetificado'))
    cetificaso_sat = fields.Char(string=_('Cetificao SAT'))
    folio_fiscal = fields.Char(string=_('Folio Fiscal'), readonly=True)
    fecha_certificacion = fields.Char(string=_('Fecha y Hora Certificación'))
    cadena_origenal = fields.Char(string=_('Cadena Origenal del Complemento digital de SAT'))
    selo_digital_cdfi = fields.Char(string=_('Selo Digital del CDFI'))
    selo_sat = fields.Char(string=_('Selo del SAT'))
    moneda = fields.Char(string=_('Moneda'))
    tipocambio = fields.Char(string=_('TipoCambio'))
    folio = fields.Char(string=_('Folio'))
    version = fields.Char(string=_('Version'))
    serie_emisor = fields.Char(string=_('Serie'))
    invoice_datetime = fields.Char(string=_('fecha factura'))
    rfc_emisor = fields.Char(string=_('RFC'))
    total_nomina = fields.Float('Total a pagar')
    subtotal = fields.Float('Subtotal')
    descuento = fields.Float('Descuento')
    deducciones_lines = []
    number_folio = fields.Char(string=_('Folio'), compute='_get_number_folio')
    fecha_factura = fields.Datetime(string=_('Fecha Factura'), readonly=True)
    subsidio_periodo = fields.Float('subsidio_periodo')
    isr_periodo = fields.Float('isr_periodo')
    retencion_subsidio_pagado = fields.Float('retencion_subsidio_pagado')
    importe_imss = fields.Float('importe_imss')
    importe_isr = fields.Float('importe_isr')
    periodicidad = fields.Float('periodicidad')
    concepto_periodico = fields.Boolean('Conceptos periodicos', default = True)
    #septimo_dia = fields.Boolean(string='Proporcional septimo día')
    #incapa_sept_dia = fields.Boolean(string='Incluir incapacidades 7mo día')

    #desglose imss
    prestaciones  = fields.Float('prestaciones')
    invalli_y_vida  = fields.Float('invalli_y_vida')
    cesantia_y_vejez = fields.Float('cesantia_y_vejez')
    pensio_y_benefi  = fields.Float('pensio_y_benefi')

    forma_pago = fields.Selection(
        selection=[('99', '99 - Por definir'),],
        string=_('Forma de pago'),default='99',
    )	
    tipo_comprobante = fields.Selection(
        selection=[('N', 'Nómina'),],
        string=_('Tipo de comprobante'),default='N',
    )	
    tipo_relacion = fields.Selection(
        selection=[('04', 'Sustitución de los CFDI previos'),],
        string=_('Tipo relación'),
    )
    uuid_relacionado = fields.Char(string=_('CFDI Relacionado'))
    methodo_pago = fields.Selection(
        selection=[('PUE', _('Pago en una sola exhibición')),],
        string=_('Método de pago'), default='PUE',
    )	
    uso_cfdi = fields.Selection(
        selection=[('P01', _('Por definir')),],
        string=_('Uso CFDI (cliente)'),default='P01',
    )
    fecha_pago = fields.Date(string=_('Fecha de pago'))
    dias_pagar = fields.Float('Pagar en la nomina')
    no_nomina = fields.Selection(
        selection=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6')], string=_('Nómina del mes'))
    acum_per_totales = fields.Float('Percepciones totales', compute='_get_percepciones_totales')
    acum_per_grav  = fields.Float('Percepciones gravadas', compute='_get_percepciones_gravadas')
    acum_isr  = fields.Float('ISR', compute='_get_isr')
    acum_isr_antes_subem  = fields.Float('ISR antes de SUBEM', compute='_get_isr_antes_subem')
    acum_subsidio_aplicado  = fields.Float('Subsidio aplicado', compute='_get_subsidio_aplicado')
    acum_fondo_ahorro = fields.Float('Fondo ahorro', compute='_get_fondo_ahorro')
    dias_periodo = fields.Float(string=_('Dias en el periodo'), compute='_get_dias_periodo')
    isr_devolver = fields.Boolean(string='Devolver ISR')
    isr_ajustar = fields.Boolean(string='Ajustar ISR en cada nómina')
    acum_sueldo = fields.Float('Sueldo', compute='_get_sueldo')

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
        string=_('Mes de la nómina'))

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        horas_obj = self.env['horas.nomina']
        tipo_de_hora_mapping = {'1':'HEX1', '2':'HEX2', '3':'HEX3'}
        
        def is_number(s):
            try:
                return float(s)
            except ValueError:
                return 0

        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.datetime.combine(fields.Date.from_string(date_from), datetime.time.min)
            day_to = datetime.datetime.combine(fields.Date.from_string(date_to), datetime.time.max)

            # compute Prima vacacional
            if contract.tipo_prima_vacacional == '01':
               date_start = contract.date_start
               if date_start:
                   d_from = fields.Date.from_string(date_from)
                   d_to = fields.Date.from_string(date_to)

                   date_start = fields.Date.from_string(date_start)
                   d_from = d_from.replace(date_start.year)
                   d_to = d_to.replace(date_start.year)

                   if d_from <= date_start <= d_to:
                       antiguedad_anos = contract.antiguedad_anos
                       tabla_antiguedades = contract.tablas_cfdi_id.tabla_antiguedades.filtered(lambda x: x.antiguedad <= antiguedad_anos)
                       tabla_antiguedades = tabla_antiguedades.sorted(lambda x:x.antiguedad, reverse=True)
                       vacaciones = tabla_antiguedades and tabla_antiguedades[0].vacaciones or 0
                       attendances = {
                           'name': 'Prima vacacional',
                           'sequence': 2,
                           'code': 'PVC',
                           'number_of_days': vacaciones, #work_data['days'],
                           #'number_of_hours': 1['hours'],
                           'contract_id': contract.id,
                       }
                       res.append(attendances)

            # compute leave days
            leaves = {}
            leave_days = 0
            factor = 0
            if contract.semana_inglesa:
                factor = 7.0/5.0
            else:
                factor = 7.0/6.0

            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to, calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.name or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                #current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.datetime.combine(day, datetime.time.min)),
                    tz.localize(datetime.datetime.combine(day, datetime.time.max)),
                    compute_leaves=False,
                )
                if work_hours and contract.septimo_dia:
                    if holiday.holiday_status_id.name == 'FJS' or holiday.holiday_status_id.name == 'FI':
                       leave_days += (hours / work_hours)*factor
                       current_leave_struct['number_of_days'] += (hours / work_hours)*factor
                    else:
                       leave_days += hours / work_hours
                       current_leave_struct['number_of_days'] += hours / work_hours
                elif work_hours:
                    leave_days += hours / work_hours
                    current_leave_struct['number_of_days'] += hours / work_hours

            # compute worked days
            work_data = contract.employee_id.get_work_days_data(day_from, day_to, calendar=contract.resource_calendar_id)
            number_of_days = 0

            #dias_a_pagar = contract.dias_pagar
            _logger.info('dias trabajados %s  dias incidencia %s', work_data['days'], leave_days)

            #periodo para nómina quincenal
            if contract.periodicidad_pago == '04' and contract.tipo_pago == '01':
                total_days = work_data['days'] + leave_days
                if total_days != 15:
                   number_of_days = 15 - leave_days
                else:
                   number_of_days = work_data['days']
            elif contract.periodicidad_pago == '02':
                if contract.septimo_dia:
                   total_days = work_data['days'] + leave_days
                   if total_days != 7:
                      number_of_days = 7 - leave_days
                   else:
                      number_of_days = work_data['days']
                if contract.sept_dia:
                   if number_of_days == 0:
                      number_of_days = work_data['days']
                   aux = number_of_days - int(number_of_days)
                   if aux > 0:
                      number_of_days -=  aux
                   else:
                      aux = 1
                      number_of_days -=  aux
                   attendances = {
                       'name': _("Séptimo día"),
                       'sequence': 3,
                       'code': "SEPT",
                       'number_of_days': aux, 
                       'number_of_hours': 0.0,
                       'contract_id': contract.id,
                   }
                   res.append(attendances)
            else:
                number_of_days = work_data['days']
            attendances = {
                'name': _("Días de trabajo"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': number_of_days, #work_data['days'],
                'number_of_hours': 0.0, # work_data['hours'],
                'contract_id': contract.id,
            }

            res.append(attendances)

            #Compute horas extas
            horas = horas_obj.search([('employee_id','=',contract.employee_id.id),('fecha','>=',date_from), ('fecha', '<=', date_to)])
            horas_by_tipo_de_horaextra = defaultdict(list)
            for h in horas:
                horas_by_tipo_de_horaextra[h.tipo_de_hora].append(h.horas)
            
            for tipo_de_hora, horas_set in horas_by_tipo_de_horaextra.items():
                work_code = tipo_de_hora_mapping.get(tipo_de_hora,'')
                number_of_days = len(horas_set)
                number_of_hours = sum(is_number(hs) for hs in horas_set)
                     
                attendances = {
                    'name': _("Horas extras"),
                    'sequence': 2,
                    'code': work_code,
                    'number_of_days': number_of_days, 
                    'number_of_hours': number_of_hours,
                    'contract_id': contract.id,
                }
                res.append(attendances)
                
            res.extend(leaves.values())
        
        return res

    @api.multi
    def set_fecha_pago(self, payroll_name):
            values = {
                'payslip_run_id': payroll_name
                }
            self.update(values)
	
    @api.multi
    @api.onchange('date_to')
    def _get_fecha_pago(self):
        if self.date_to:
            values = {
                'fecha_pago': self.date_to
                }
            self.update(values)

    @api.multi
    @api.onchange('date_to')
    def _get_dias_periodo(self):
        self.dias_periodo = 0
        if self.date_to and self.date_from and self.contract_id.periodicidad_pago == '02':
            line = self.contract_id.env['tablas.periodo.semanal'].search([('form_id','=',self.contract_id.tablas_cfdi_id.id),('dia_fin','>=',self.date_to),
                                                                    ('dia_inicio','<=',self.date_to)],limit=1)
            if line:
                _logger.info('encontró periodo..%s', line.no_periodo)
                self.dias_periodo = line.no_dias
            else:
                raise UserError(_('No están configurados correctamente los periodos semanales en las tablas CFDI'))

    @api.model
    def create(self, vals):
        if not vals.get('fecha_pago') and vals.get('date_to'):
            vals.update({'fecha_pago': vals.get('date_to')})
            
        res = super(HrPayslip, self).create(vals)
        return res
    
    @api.depends('number')
    @api.one
    def _get_number_folio(self):
        if self.number:
            self.number_folio = self.number.replace('SLIP','').replace('/','')

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if self.estado_factura == 'factura_correcta':
            default['estado_factura'] = 'factura_no_generada'
            default['folio_fiscal'] = ''
            default['fecha_factura'] = None
            default['nomina_cfdi'] = False
        return super(HrPayslip, self).copy(default=default)

    @api.multi
    @api.onchange('mes')
    def _get_percepciones_gravadas(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'TPERG')])
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
        self.acum_per_grav = total

    @api.multi
    @api.onchange('mes')
    def _get_isr(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'ISR2'),('category_id.code','=','DED')])
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
        self.acum_isr = total

    @api.multi
    @api.onchange('mes')
    def _get_isr_antes_subem(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'ISR')])
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
        self.acum_isr_antes_subem = total

    @api.multi
    @api.onchange('mes')
    def _get_subsidio_aplicado(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'SUB')])
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
        self.acum_subsidio_aplicado = total

    @api.multi
    @api.onchange('mes')
    def _get_fondo_ahorro(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'D067'),('category_id.code','=','DED')])
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
        self.acum_fondo_ahorro = total

    @api.multi
    @api.onchange('mes')
    def _get_percepciones_totales(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio
            date_end = mes_actual.dia_fin
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'TPER')])
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
        self.acum_per_totales = total

    @api.multi
    @api.onchange('mes')
    def _get_sueldo(self):
        total = 0
        if self.employee_id and self.mes and self.contract_id.tablas_cfdi_id:
            mes_actual = self.env['tablas.periodo.mensual'].search([('mes', '=', self.mes)])[0]
            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', 'P001')])
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
        self.acum_sueldo = total

    @api.model
    def to_json(self):
        payslip_total_TOP = 0
        payslip_total_TDED = 0
        payslip_total_PERG = 0
        payslip_total_PERE = 0
        payslip_total_SEIN = 0
        payslip_total_JPRE = 0
        antiguedad = 1
        if self.contract_id.date_end and self.contract_id.date_start:
            antiguedad = int((self.contract_id.date_end - self.contract_id.date_start + timedelta(days=1)).days/7)
        elif self.date_to and self.contract_id.date_start:
            antiguedad = int((self.date_to - self.contract_id.date_start + timedelta(days=1)).days/7)

#**********  Percepciones ************
        total_percepciones_lines = self.env['hr.payslip.line'].search(['|',('category_id.code','=','ALW'),('code','=','P001'),('category_id.code','=','ALW3'),('slip_id','=',self.id)])
        percepciones_grabadas_lines = self.env['hr.payslip.line'].search(['|',('category_id.code','=','ALW'),('code','=','P001'),('slip_id','=',self.id)])
        lineas_de_percepcion = []
        tipo_percepcion_dict = dict(self.env['hr.salary.rule']._fields.get('tipo_percepcion').selection)
        if percepciones_grabadas_lines:
            for line in percepciones_grabadas_lines:
                if line.salary_rule_id.tipo_percepcion != '022' and line.salary_rule_id.tipo_percepcion != '023' and line.salary_rule_id.tipo_percepcion != '025' and line.salary_rule_id.tipo_percepcion !='039' and line.salary_rule_id.tipo_percepcion !='044':
                    payslip_total_PERG += round(line.total,2)
                lineas_de_percepcion.append({'TipoPercepcion': line.salary_rule_id.tipo_percepcion,
                'Clave': line.code,
                'Concepto': tipo_percepcion_dict.get(line.salary_rule_id.tipo_percepcion),
                'ImporteGravado': line.total,
                'ImporteExento': '0'})
                if line.salary_rule_id.tipo_percepcion == '022' or line.salary_rule_id.tipo_percepcion == '023' or line.salary_rule_id.tipo_percepcion == '025':
                    payslip_total_SEIN += round(line.total,2)
                if line.salary_rule_id.tipo_percepcion =='039' or line.salary_rule_id.tipo_percepcion =='044':
                    payslip_total_JPRE += round(line.total,2)

        percepciones_excentas_lines = self.env['hr.payslip.line'].search([('category_id.code','=','ALW2'),('slip_id','=',self.id)])
        lineas_de_percepcion_exentas = []
        if percepciones_excentas_lines:
            for line in percepciones_excentas_lines:
                parte_exenta = 0
                parte_gravada = 0

                #fondo ahorro
                if line.salary_rule_id.tipo_percepcion == '005':
                    if line.total > self.contract_id.tablas_cfdi_id.ex_fondo_ahorro:
                        parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_fondo_ahorro
                        parte_exenta = self.contract_id.tablas_cfdi_id.ex_fondo_ahorro
                    else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #prima dominical
                if line.salary_rule_id.tipo_percepcion == '020':
                    if line.total > self.contract_id.tablas_cfdi_id.ex_prima_dominical:
                        parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_prima_dominical
                        parte_exenta = self.contract_id.tablas_cfdi_id.ex_prima_dominical
                    else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #vale de despensa
                if  line.salary_rule_id.tipo_percepcion == '029':
                    if line.total > self.contract_id.tablas_cfdi_id.ex_vale_despensa:
                        parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_vale_despensa
                        parte_exenta = self.contract_id.tablas_cfdi_id.ex_vale_despensa
                    else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #aguinaldo
                if line.salary_rule_id.tipo_percepcion == '002':
                    if line.total > self.contract_id.tablas_cfdi_id.ex_aguinaldo:
                        parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_aguinaldo
                        parte_exenta = self.contract_id.tablas_cfdi_id.ex_aguinaldo
                    else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #reparto de utlidades
                if line.salary_rule_id.tipo_percepcion == '003':
                    if line.total > self.contract_id.tablas_cfdi_id.ex_ptu:
                        parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_ptu
                        parte_exenta = self.contract_id.tablas_cfdi_id.ex_ptu
                    else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #prima vacacional diario
                if line.salary_rule_id.tipo_percepcion == '021': #and line.salary_rule_id.sequence == 120:
                    antiguedad_anos = self.contract_id.antiguedad_anos
                    dias_vacaciones = 0
                    if self.contract_id.tablas_cfdi_id:
                        line2 = self.contract_id.env['tablas.antiguedades.line'].search([('form_id','=',self.contract_id.tablas_cfdi_id.id),('antiguedad','<=',antiguedad_anos)],order='antiguedad desc',limit=1)
                        if line2:
                            dias_vacaciones = line2.vacaciones

                    dias_prima_vac = self.env['hr.payslip.worked_days'].search(['|',('payslip_id','=',self.id),('code','=','VAC')]) #l,imit=1
                    dias_vac = 0
                    if dias_prima_vac:
                        _logger.info('si hay dias vacaciones..')
                        for dias_vac_line in dias_prima_vac:
                            dias_vac = dias_vac_line.number_of_days

                    monto_max = self.contract_id.tablas_cfdi_id.ex_prima_vacacional / dias_vacaciones * dias_vac
                    if line.total > monto_max:
                        parte_gravada = line.total - monto_max
                        parte_exenta = monto_max
                    else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #prima vaccional completo
                #if line.salary_rule_id.tipo_percepcion == '021' and line.salary_rule_id.sequence == 122:
                #    _logger.info('entro a prima vacacional')
                #    if line.total > self.contract_id.tablas_cfdi_id.ex_prima_vacacional:
                #        parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_prima_vacacional
                #        parte_exenta = self.contract_id.tablas_cfdi_id.ex_prima_vacacional
                #    else:
                #        parte_exenta = line.total
                #        parte_gravada = 0

                #viaticos
                if line.salary_rule_id.tipo_percepcion == '050':
                    #if line.total > self.contract_id.tablas_cfdi_id.ex_ptu:
                    #    parte_gravada = line.total - self.contract_id.tablas_cfdi_id.ex_ptu
                    #    parte_exenta = self.contract_id.tablas_cfdi_id.ex_ptu
                    #else:
                        parte_exenta = line.total
                        parte_gravada = 0

                #nomina de liquidacion / finiquito
                if line.salary_rule_id.tipo_percepcion == '022' or line.salary_rule_id.tipo_percepcion == '023' or line.salary_rule_id.tipo_percepcion == '025':
                #calculo total indemnizacion
                    total_indemnizacion = 0
                    percepciones_liquidacion = self.env['hr.payslip.line'].search([('category_id.code','=','ALW2'),('slip_id','=',self.id)])
                    if percepciones_liquidacion:
                        for line3 in percepciones_liquidacion:
                            if line3.salary_rule_id.tipo_percepcion == '022' or line3.salary_rule_id.tipo_percepcion == '023' or line3.salary_rule_id.tipo_percepcion == '025':
                                total_indemnizacion += line3.total
                    #indemnizacion
                    if line.salary_rule_id.tipo_percepcion == '025':
                        if total_indemnizacion > self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos:
                            parte_gravada = round(line.total - (self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos) * (line.total/total_indemnizacion),2)
                            parte_exenta = round(self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos * (line.total/total_indemnizacion),2)
                        else:
                            parte_exenta = line.total
                            parte_gravada = 0

                    #prima de antiguedad
                    if line.salary_rule_id.tipo_percepcion == '022':
                        if total_indemnizacion > self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos:
                            parte_gravada = round(line.total - (self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos) * (line.total/total_indemnizacion),2)
                            parte_exenta = round(self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos * (line.total/total_indemnizacion),2)
                        else:
                            parte_exenta = line.total
                            parte_gravada = 0

                    #pagos por separacion
                    if line.salary_rule_id.tipo_percepcion == '023':
                        if total_indemnizacion > self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos:
                            parte_gravada = round(line.total - (self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos) * (line.total/total_indemnizacion),2)
                            parte_exenta = round(self.contract_id.tablas_cfdi_id.ex_liquidacion * self.contract_id.antiguedad_anos * (line.total/total_indemnizacion),2)
                        else:
                            parte_exenta = line.total
                            parte_gravada = 0

                # obtener totales
                #if line.salary_rule_id.tipo_percepcion != '022' and line.salary_rule_id.tipo_percepcion != '023' and line.salary_rule_id.tipo_percepcion != '025' and line.salary_rule_id.tipo_percepcion !='039' and line.salary_rule_id.tipo_percepcion !='044':
                if line.salary_rule_id.tipo_percepcion !='039' and line.salary_rule_id.tipo_percepcion !='044':
                    payslip_total_PERE += round(parte_exenta,2)
                    payslip_total_PERG += round(parte_gravada,2)
                if line.salary_rule_id.tipo_percepcion == '022' or line.salary_rule_id.tipo_percepcion == '023' or line.salary_rule_id.tipo_percepcion == '025':
                    payslip_total_SEIN += round(line.total,2)
                if line.salary_rule_id.tipo_percepcion =='039' or line.salary_rule_id.tipo_percepcion =='044':
                    payslip_total_JPRE += round(line.total,2)

                # horas extras
                if line.salary_rule_id.tipo_percepcion == '019':
                    percepciones_horas_extras = self.env['hr.payslip.worked_days'].search([('payslip_id','=',self.id)])
                    if percepciones_horas_extras:
                        _logger.info('si hay ..')
                        for ext_line in percepciones_horas_extras:
                            #_logger.info('codigo %s.....%s ', line.code, ext_line.code)
                            if line.code == ext_line.code:
                                if line.code == 'HEX1':
                                    tipo_hr = '03'
                                elif line.code == 'HEX2':
                                    tipo_hr = '01'
                                elif line.code == 'HEX3':
                                    tipo_hr = '02'
                                lineas_de_percepcion_exentas.append({'TipoPercepcion': line.salary_rule_id.tipo_percepcion,
                             'Clave': line.code,
                             'Concepto': tipo_percepcion_dict.get(line.salary_rule_id.tipo_percepcion),
                             'ImporteGravado': parte_gravada,
                             'ImporteExento': parte_exenta,
                             'Dias': ext_line.number_of_days,
                             'TipoHoras': tipo_hr,
                             'HorasExtra': ext_line.number_of_hours,
                             'ImportePagado': line.total})
                # Jubilaciones, pensiones o haberes de retiro en una exhibición
                #elif line.salary_rule_id.tipo_percepcion == '039':

                # Jubilaciones, pensiones o haberes de retiro en parcialidades
                #elif line.salary_rule_id.tipo_percepcion == '044':

                # Ingresos en acciones o títulos valor que representan bienes
                elif line.salary_rule_id.tipo_percepcion == '045':
                    lineas_de_percepcion_exentas.append({'TipoPercepcion': line.salary_rule_id.tipo_percepcion,
                   'Clave': line.code,
                   'Concepto': tipo_percepcion_dict.get(line.salary_rule_id.tipo_percepcion),
                   'ValorMercado': 56,
                   'PrecioAlOtorgarse': 48,
                   'ImporteGravado': parte_gravada,
                   'ImporteExento': parte_exenta})
                else:
                    lineas_de_percepcion_exentas.append({'TipoPercepcion': line.salary_rule_id.tipo_percepcion,
                   'Clave': line.code,
                   'Concepto': tipo_percepcion_dict.get(line.salary_rule_id.tipo_percepcion),
                   'ImporteGravado': parte_gravada,
                   'ImporteExento': parte_exenta})

        percepcion = {
               'Totalpercepcion': {
                        'TotalSeparacionIndemnizacion': payslip_total_SEIN,
                        'TotalJubilacionPensionRetiro': payslip_total_JPRE,
                        'TotalGravado': payslip_total_PERG,
                        'TotalExento': payslip_total_PERE,
                        'TotalSueldos': payslip_total_PERG + payslip_total_PERE - payslip_total_SEIN - payslip_total_JPRE,
               },
        }

        #************ SEPARACION / INDEMNIZACION   ************#
        if payslip_total_SEIN > 0:
            if payslip_total_PERG > self.contract_id.wage:
                ingreso_acumulable = self.contract_id.wage
            else:
                ingreso_acumulable = payslip_total_PERG
            if payslip_total_PERG - self.contract_id.wage < 0:
                ingreso_no_acumulable = 0
            else:
                ingreso_no_acumulable = payslip_total_PERG - self.contract_id.wage

            percepcion.update({
               'separacion': [{
                        'TotalPagado': payslip_total_SEIN,
                        'NumAñosServicio': self.contract_id.antiguedad_anos,
                        'UltimoSueldoMensOrd': self.contract_id.wage,
                        'IngresoAcumulable': ingreso_acumulable,
                        'IngresoNoAcumulable': ingreso_no_acumulable,
                }]
            })
            #percepcion.update({'SeparacionIndemnizacion': separacion})


        percepcion.update({'lineas_de_percepcion_grabadas': lineas_de_percepcion, 'no_per_grabadas': len(percepciones_grabadas_lines)})
        percepcion.update({'lineas_de_percepcion_excentas': lineas_de_percepcion_exentas, 'no_per_excentas': len(percepciones_excentas_lines)})
        request_params = {'percepciones': percepcion}

#****** OTROS PAGOS ******
        otrospagos_lines = self.env['hr.payslip.line'].search([('category_id.code','=','ALW3'),('slip_id','=',self.id)])
        tipo_otro_pago_dict = dict(self.env['hr.salary.rule']._fields.get('tipo_otro_pago').selection)
        auxiliar_lines = self.env['hr.payslip.line'].search([('category_id.code','=','AUX'),('slip_id','=',self.id)])
        #tipo_otro_pago_dict = dict(self.env['hr.salary.rule']._fields.get('tipo_otro_pago').selection)
        lineas_de_otros = []
        if otrospagos_lines:
            for line in otrospagos_lines:
                #_#logger.info('line total ...%s', line.total)
                if line.salary_rule_id.tipo_otro_pago == '002' and line.total > 0:
                    line2 = self.contract_id.env['tablas.subsidio.line'].search([('form_id','=',self.contract_id.tablas_cfdi_id.id),('lim_inf','<=',self.contract_id.wage)],order='lim_inf desc',limit=1)
                    self.subsidio_periodo = 0
                    #_logger.info('entro a este ..')
                    payslip_total_TOP += line.total
                    #if line2:
                    #    self.subsidio_periodo = (line2.s_mensual/self.imss_mes)*self.imss_dias
                    for aux in auxiliar_lines:
                        if aux.code == 'SUB':
                            self.subsidio_periodo = aux.total
                    _logger.info('subsidio aplicado %s importe excento %s', self.subsidio_periodo, line.total)
                    lineas_de_otros.append({'TipoOtrosPagos': line.salary_rule_id.tipo_otro_pago,
                    'Clave': line.code,
                    'Concepto': tipo_otro_pago_dict.get(line.salary_rule_id.tipo_otro_pago),
                    'ImporteGravado': '0',
                    'ImporteExento': line.total,
                    'SubsidioCausado': self.subsidio_periodo})
                else:
                    payslip_total_TOP += line.total
                    #_logger.info('entro al otro ..')
                    lineas_de_otros.append({'TipoOtrosPagos': line.salary_rule_id.tipo_otro_pago,
                        'Clave': line.code,
                        'Concepto': tipo_otro_pago_dict.get(line.salary_rule_id.tipo_otro_pago),
                        'ImporteGravado': '0',
                        'ImporteExento': line.total})
        otrospagos = {
            'otrospagos': {
                    'Totalotrospagos': payslip_total_TOP,
            },
        }
        otrospagos.update({'otros_pagos': lineas_de_otros, 'no_otros_pagos': len(otrospagos_lines)})
        request_params.update({'otros_pagos': otrospagos})

#********** DEDUCCIONES *********
        total_imp_ret = 0
        suma_deducciones = 0
        self.importe_isr = 0
        self.isr_periodo = 0
        no_deuducciones = 0 #len(self.deducciones_lines)
        self.deducciones_lines = self.env['hr.payslip.line'].search([('category_id.code','=','DED'),('slip_id','=',self.id)])
        #ded_impuestos_lines = self.env['hr.payslip.line'].search([('category_id.name','=','Deducciones'),('code','=','301'),('slip_id','=',self.id)],limit=1)
        tipo_deduccion_dict = dict(self.env['hr.salary.rule']._fields.get('tipo_deduccion').selection)
        #if ded_impuestos_lines:
        #   total_imp_ret = round(ded_impuestos_lines.total,2)
        lineas_deduccion = []
        if self.deducciones_lines:
            #_logger.info('entro deduciones ...')
            #todas las deducciones excepto imss e isr
            for line in self.deducciones_lines:
                if line.salary_rule_id.tipo_deduccion != '001' and line.salary_rule_id.tipo_deduccion != '002':
                    #_logger.info('linea  ...')
                    no_deuducciones += 1
                    lineas_deduccion.append({'TipoDeduccion': line.salary_rule_id.tipo_deduccion,
                   'Clave': line.code,
                   'Concepto': tipo_deduccion_dict.get(line.salary_rule_id.tipo_deduccion),
                   'Importe': round(line.total,2)})
                    payslip_total_TDED += round(line.total,2)

            #todas las deducciones imss
            self.importe_imss = 0
            for line in self.deducciones_lines:
                if line.salary_rule_id.tipo_deduccion == '001':
                    #_logger.info('linea imss ...')
                    self.importe_imss += round(line.total,2)

            if self.importe_imss > 0:
                no_deuducciones += 1
                self.calculo_imss()
                lineas_deduccion.append({'TipoDeduccion': '001',
                  'Clave': '302',
                  'Concepto': 'Seguridad social',
                  'Importe': round(self.importe_imss,2)})
                payslip_total_TDED += round(self.importe_imss,2)

            #todas las deducciones isr
            for line in self.deducciones_lines:
                if line.salary_rule_id.tipo_deduccion == '002' and line.salary_rule_id.code == 'ISR':
                    self.isr_periodo = line.total 
                if line.salary_rule_id.tipo_deduccion == '002':
                    #_logger.info('linea ISR ...')
                    self.importe_isr += round(line.total,2)

            if self.importe_isr > 0:
                no_deuducciones += 1
                lineas_deduccion.append({'TipoDeduccion': '002',
                  'Clave': '301',
                  'Concepto': 'ISR',
                  'Importe': round(self.importe_isr,2)})
                payslip_total_TDED += round(self.importe_isr,2)
            total_imp_ret = round(self.importe_isr,2)

        deduccion = {
            'TotalDeduccion': {
                    'TotalOtrasDeducciones': round(payslip_total_TDED - total_imp_ret,2),
                    'TotalImpuestosRetenidos': total_imp_ret,
            },
        }
        deduccion.update({'lineas_de_deduccion': lineas_deduccion, 'no_deuducciones': no_deuducciones})
        request_params.update({'deducciones': deduccion})

        #************ INCAPACIDADES  ************#
        incapacidades = self.env['hr.payslip.worked_days'].search([('payslip_id','=',self.id)])
        if incapacidades:
            for ext_line in incapacidades:
                if ext_line.code == 'INC_RT' or ext_line.code == 'INC_EG' or ext_line.code == 'INC_MAT':
                    _logger.info('codigo %s.... ', ext_line.code)
                    tipo_inc = ''
                    if ext_line.code == 'INC_RT':
                        tipo_inc = '01'
                    elif ext_line.code == 'INC_EG':
                        tipo_inc = '02'
                    elif ext_line.code == 'INC_MAT':
                        tipo_inc = '03'
                    incapacidad = {
                  'Incapacidad': {
                        'DiasIncapacidad': ext_line.number_of_days,
                        'TipoIncapacidad': tipo_inc,
                        'ImporteMonetario': 0,
                        },
                        }
                    request_params.update({'incapacidades': incapacidad})

        self.retencion_subsidio_pagado = self.isr_periodo - self.subsidio_periodo
        self.total_nomina = payslip_total_PERG + payslip_total_PERE + payslip_total_TOP - payslip_total_TDED
        self.subtotal =  payslip_total_PERG + payslip_total_PERE + payslip_total_TOP
        self.descuento = payslip_total_TDED

        if self.tipo_nomina == 'O':
            self.periodicdad = self.contract_id.periodicidad_pago
        else:
            self.periodicdad = '99'
        diaspagados = 0
        if self.struct_id.name == 'Reparto de utilidades':
            diaspagados = 365
        else:
            if self.date_to and self.date_from:
               diaspagados = (self.date_to - self.date_from + timedelta(days=1)).days
        regimen = 0
        contrato = 0
        if self.struct_id.name == 'Liquidación - indemnizacion/finiquito':
            regimen = '13'
            contrato = '99'
        else:
            regimen = self.employee_id.regimen
            contrato = self.employee_id.contrato

        request_params.update({
                'factura': {
                      'serie': self.company_id.serie_nomina,
                      'folio': self.number_folio,
                      'metodo_pago': self.methodo_pago,
                      'forma_pago': self.forma_pago,
                      'tipocomprobante': self.tipo_comprobante,
                      'moneda': 'MXN',
                      'tipodecambio': '1.0000',
                      'fecha_factura': self.fecha_factura and self.fecha_factura.strftime(DTF),
                      'LugarExpedicion': self.company_id.zip,
                      'RegimenFiscal': self.company_id.regimen_fiscal,
                      'subtotal': self.subtotal,
                      'descuento': self.descuento,
                      'total': self.total_nomina,
                },
                'emisor': {
                      'rfc': self.company_id.rfc,
                      'api_key': self.company_id.proveedor_timbrado,
                      'modo_prueba': self.company_id.modo_prueba,
                      'nombre_fiscal': self.company_id.nombre_fiscal,
                      'telefono_sms': self.company_id.telefono_sms,
                },
                'receptor': {
                      'rfc': self.employee_id.rfc,
                      'nombre': self.employee_id.name,
                      'uso_cfdi': self.uso_cfdi,
                },
                'conceptos': {
                      'cantidad': '1.0',
                      'ClaveUnidad': 'ACT',
                      'ClaveProdServ': '84111505',
                      'descripcion': 'Pago de nómina',
                      'valorunitario': self.subtotal,
                      'importe':  self.subtotal,
                      'descuento': self.descuento,
                },
                'nomina12': {
                      'TipoNomina': self.tipo_nomina,
                      'FechaPago': self.fecha_pago and self.fecha_pago.strftime(DF),
                      'FechaInicialPago': self.date_from and self.date_from.strftime(DF),
                      'FechaFinalPago': self.date_to and self.date_to.strftime(DF),
                      'NumDiasPagados': diaspagados,
                      'TotalPercepciones': payslip_total_PERG + payslip_total_PERE,
                      'TotalDeducciones': self.descuento,
                      'TotalOtrosPagos': payslip_total_TOP,
                },
                'nomina12Emisor': {
                      'RegistroPatronal': self.employee_id.registro_patronal,
                      'RfcPatronOrigen': self.company_id.rfc,
                },
                'nomina12Receptor': {
                      'ClaveEntFed': self.employee_id.estado.code,
                      'Curp': self.employee_id.curp,
                      'NumEmpleado': self.employee_id.no_empleado,
                      'PeriodicidadPago': self.periodicdad, #self.contract_id.periodicidad_pago,
                      'TipoContrato': contrato,
                      'TipoRegimen': regimen,
                      'TipoJornada': self.employee_id.jornada,
                      'Antiguedad': 'P' + str(antiguedad) + 'W',
                      'Banco': self.employee_id.banco.c_banco,
                      'CuentaBancaria': self.employee_id.no_cuenta,
                      'FechaInicioRelLaboral': self.contract_id.date_start and self.contract_id.date_start.strftime(DF),
                      'NumSeguridadSocial': self.employee_id.segurosocial,
                      'Puesto': self.employee_id.job_id.name,
                      'Departamento': self.employee_id.department_id.name,
                      'RiesgoPuesto': self.contract_id.riesgo_puesto,
                      'SalarioBaseCotApor': self.contract_id.sueldo_diario_integrado,
                      'SalarioDiarioIntegrado': self.contract_id.sueldo_diario_integrado,
                },
		})

#****** CERTIFICADOS *******
        if not self.company_id.archivo_cer:
            raise UserError(_('Archivo .cer path is missing.'))
        if not self.company_id.archivo_key:
            raise UserError(_('Archivo .key path is missing.'))
        archivo_cer = self.company_id.archivo_cer
        archivo_key = self.company_id.archivo_key
        request_params.update({
                'certificados': {
                      'archivo_cer': archivo_cer.decode("utf-8"),
                      'archivo_key': archivo_key.decode("utf-8"),
                      'contrasena': self.company_id.contrasena,
                }})
        return request_params

    @api.multi
    def action_cfdi_nomina_generate(self):
        for payslip in self:
            if payslip.fecha_factura == False:
                payslip.fecha_factura= datetime.datetime.now()
                payslip.write({'fecha_factura': payslip.fecha_factura})
            if payslip.estado_factura == 'factura_correcta':
                raise UserError(_('Error para timbrar factura, Factura ya generada.'))
            if payslip.estado_factura == 'factura_cancelada':
                raise UserError(_('Error para timbrar factura, Factura ya generada y cancelada.'))

            values = payslip.to_json()
            #  print json.dumps(values, indent=4, sort_keys=True)
            if payslip.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/nomina')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % ('http://facturacion2.itadmin.com.mx/api/nomina')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % ('http://facturacion3.itadmin.com.mx/api/nomina')
            elif payslip.company_id.proveedor_timbrado == 'gecoerp':
                if self.company_id.modo_prueba:
                    url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/nomina/?handler=OdooHandler33')
                else:
                    url = '%s' % ('https://itadmin.gecoerp.com/nomina/?handler=OdooHandler33')

            response = requests.post(url,auth=None,verify=False, data=json.dumps(values),headers={"Content-type": "application/json"})

            _logger.info('something ... %s', response.text)
            json_response = response.json()
            xml_file_link = False
            estado_factura = json_response['estado_factura']
            if estado_factura == 'problemas_factura':
                raise UserError(_(json_response['problemas_message']))
            # Receive and stroe XML 
            if json_response.get('factura_xml'):
                xml_file_link = payslip.company_id.factura_dir + '/' + payslip.name.replace('/', '_') + '.xml'
                xml_file = open(xml_file_link, 'w')
                xml_payment = base64.b64decode(json_response['factura_xml'])
                xml_file.write(xml_payment.decode("utf-8"))
                xml_file.close()
                payslip._set_data_from_xml(xml_payment)
                    
                xml_file_name = payslip.name.replace('/', '_') + '.xml'
                self.env['ir.attachment'].sudo().create(
                                            {
                                                'name': xml_file_name,
                                                'datas': json_response['factura_xml'],
                                                'datas_fname': xml_file_name,
                                                'res_model': self._name,
                                                'res_id': payslip.id,
                                                'type': 'binary'
                                            })	
                report = self.env['ir.actions.report']._get_report_from_name('nomina_cfdi.report_payslip')
                report_data = report.render_qweb_pdf([payslip.id])[0]
                pdf_file_name = payslip.name.replace('/', '_') + '.pdf'
                self.env['ir.attachment'].sudo().create(
                                            {
                                                'name': pdf_file_name,
                                                'datas': base64.b64encode(report_data),
                                                'datas_fname': pdf_file_name,
                                                'res_model': self._name,
                                                'res_id': payslip.id,
                                                'type': 'binary'
                                            })

            payslip.write({'estado_factura': estado_factura,
                    'xml_nomina_link': xml_file_link,
                    'nomina_cfdi': True})

    @api.one
    def _set_data_from_xml(self, xml_invoice):
        if not xml_invoice:
            return None
        NSMAP = {
                 'xsi':'http://www.w3.org/2001/XMLSchema-instance',
                 'cfdi':'http://www.sat.gob.mx/cfd/3', 
                 'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                 }

        xml_data = etree.fromstring(xml_invoice)
        Emisor = xml_data.find('cfdi:Emisor', NSMAP)
        RegimenFiscal = Emisor.find('cfdi:RegimenFiscal', NSMAP)
        Complemento = xml_data.find('cfdi:Complemento', NSMAP)
        TimbreFiscalDigital = Complemento.find('tfd:TimbreFiscalDigital', NSMAP)
        
        self.rfc_emisor = Emisor.attrib['Rfc']
        self.name_emisor = Emisor.attrib['Nombre']
        self.tipocambio = xml_data.attrib['TipoCambio']
        #  self.tipo_comprobante = xml_data.attrib['TipoDeComprobante']
        self.moneda = xml_data.attrib['Moneda']
        self.numero_cetificado = xml_data.attrib['NoCertificado']
        self.cetificaso_sat = TimbreFiscalDigital.attrib['NoCertificadoSAT']
        self.fecha_certificacion = TimbreFiscalDigital.attrib['FechaTimbrado']
        self.selo_digital_cdfi = TimbreFiscalDigital.attrib['SelloCFD']
        self.selo_sat = TimbreFiscalDigital.attrib['SelloSAT']
        self.folio_fiscal = TimbreFiscalDigital.attrib['UUID']
        self.folio = xml_data.attrib['Folio']
        self.serie_emisor = xml_data.attrib['Serie']
        self.invoice_datetime = xml_data.attrib['Fecha']
        self.version = TimbreFiscalDigital.attrib['Version']
        self.cadena_origenal = '||%s|%s|%s|%s|%s||' % (self.version, self.folio_fiscal, self.fecha_certificacion, 
                                                         self.selo_digital_cdfi, self.cetificaso_sat)
        
        options = {'width': 275 * mm, 'height': 275 * mm}
        amount_str = str(self.total_nomina).split('.')
        #print 'amount_str, ', amount_str
        qr_value = '?re=%s&rr=%s&tt=%s.%s&id=%s' % (self.company_id.rfc, 
                                                 self.employee_id.rfc,
                                                 amount_str[0].zfill(10),
                                                 amount_str[1].ljust(6, '0'),
                                                 self.folio_fiscal
                                                 )
        self.qr_value = qr_value
        ret_val = createBarcodeDrawing('QR', value=qr_value, **options)
        self.qrcode_image = base64.encodestring(ret_val.asString('jpg'))

    @api.multi
    def action_cfdi_cancel(self):
        for payslip in self:
            if payslip.nomina_cfdi:
                if payslip.estado_factura == 'factura_cancelada':
                    pass
                    # raise UserError(_('La factura ya fue cancelada, no puede volver a cancelarse.'))
                if not payslip.company_id.archivo_cer:
                    raise UserError(_('Falta la ruta del archivo .cer'))
                if not payslip.company_id.archivo_key:
                    raise UserError(_('Falta la ruta del archivo .key'))
                archivo_cer = payslip.company_id.archivo_cer
                archivo_key = payslip.company_id.archivo_key
                archivo_xml_link = payslip.company_id.factura_dir + '/' + payslip.folio_fiscal + '.xml'
                with open(archivo_xml_link, 'rb') as cf:
                     archivo_xml = base64.b64encode(cf.read())
                values = {
                          'rfc': payslip.company_id.rfc,
                          'api_key': payslip.company_id.proveedor_timbrado,
                          'uuid': self.folio_fiscal,
                          'folio': self.folio,
                          'serie_factura': payslip.company_id.serie_nomina,
                          'modo_prueba': payslip.company_id.modo_prueba,
                            'certificados': {
                                  'archivo_cer': archivo_cer.decode("utf-8"),
                                  'archivo_key': archivo_key.decode("utf-8"),
                                  'contrasena': payslip.company_id.contrasena,
                            },
                          'xml': archivo_xml.decode("utf-8"),
                          }
                if self.company_id.proveedor_timbrado == 'multifactura':
                    url = '%s' % ('http://facturacion.itadmin.com.mx/api/refund')
                elif self.company_id.proveedor_timbrado == 'multifactura2':
                    url = '%s' % ('http://facturacion2.itadmin.com.mx/api/refund')
                elif self.company_id.proveedor_timbrado == 'multifactura3':
                    url = '%s' % ('http://facturacion3.itadmin.com.mx/api/refund')
                elif self.company_id.proveedor_timbrado == 'gecoerp':
                    if self.company_id.modo_prueba:
                        url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/refund/?handler=OdooHandler33')
                        #url = '%s' % ('https://itadmin.gecoerp.com/refund/?handler=OdooHandler33')
                    else:
                        url = '%s' % ('https://itadmin.gecoerp.com/refund/?handler=OdooHandler33')
                response = requests.post(url , 
                                         auth=None,verify=False, data=json.dumps(values), 
                                         headers={"Content-type": "application/json"})
    
                #print 'Response: ', response.status_code
                json_response = response.json()
                #_logger.info('log de la exception ... %s', response.text)

                if json_response['estado_factura'] == 'problemas_factura':
                    raise UserError(_(json_response['problemas_message']))
                elif json_response.get('factura_xml', False):
                    if payslip.number:
                        xml_file_link = payslip.company_id.factura_dir + '/CANCEL_' + payslip.number.replace('/', '_') + '.xml'
                    else:
                        xml_file_link = payslip.company_id.factura_dir + '/CANCEL_' + self.folio_fiscal + '.xml'
                    xml_file = open(xml_file_link, 'w')
                    xml_invoice = base64.b64decode(json_response['factura_xml'])
                    xml_file.write(xml_invoice.decode("utf-8"))
                    xml_file.close()
                    if payslip.number:
                        file_name = payslip.number.replace('/', '_') + '.xml'
                    else:
                        file_name = self.folio_fiscal + '.xml'
                    self.env['ir.attachment'].sudo().create(
                                                {
                                                    'name': file_name,
                                                    'datas': json_response['factura_xml'],
                                                    'datas_fname': file_name,
                                                    'res_model': self._name,
                                                    'res_id': payslip.id,
                                                    'type': 'binary'
                                                })
                payslip.write({'estado_factura': json_response['estado_factura']})

    @api.multi
    def send_nomina(self):
        self.ensure_one()
        template = self.env.ref('nomina_cfdi.email_template_payroll', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
            
        ctx = dict()
        ctx.update({
            'default_model': 'hr.payslip',
            'default_res_id': self.id,
            'default_use_template': bool(template),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def fondo_ahorro(self):	
        deducciones_ahorro = self.env['hr.payslip.line'].search([('category_id.code','=','DED'),('slip_id','=',self.id)])
        if deducciones_ahorro:
            _logger.info('fondo ahorro deudccion...')
            for line in deducciones_ahorro:
                if line.salary_rule_id.tipo_deduccion == '017':
                    self.employee_id.fondo_ahorro += line.total

        percepciones_ahorro = self.env['hr.payslip.line'].search([('category_id.code','=','ALW2'),('slip_id','=',self.id)])
        if percepciones_ahorro:
            _logger.info('fondo ahorro percepcion...')
            for line in percepciones_ahorro:
                if line.salary_rule_id.tipo_percepcion == '005':
                    self.employee_id.fondo_ahorro -= line.total

    @api.model
    def devolucion_fondo_ahorro(self):	
        deducciones_ahorro = self.env['hr.payslip.line'].search([('category_id.code','=','DED'),('slip_id','=',self.id)])
        if deducciones_ahorro:
            _logger.info('Devolucion fondo ahorro deduccion...')
            for line in deducciones_ahorro:
                if line.salary_rule_id.tipo_deduccion == '017':
                    self.employee_id.fondo_ahorro -= line.total

        percepciones_ahorro = self.env['hr.payslip.line'].search([('category_id.code','=','ALW2'),('slip_id','=',self.id)])
        if percepciones_ahorro:
            _logger.info('Devolucion fondo ahorro percepcion...')
            for line in percepciones_ahorro:
                if line.salary_rule_id.tipo_percepcion == '005':
                    self.employee_id.fondo_ahorro += line.total

    @api.multi
    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        for rec in self:
            rec.fondo_ahorro()
        return res

    @api.multi
    def refund_sheet(self):
        res = super(HrPayslip, self).refund_sheet()
        for rec in self:
            rec.devolucion_fondo_ahorro()
        return res

    @api.model
    def calculo_imss(self):
        #cuota del IMSS parte del Empleado
        salario_cotizado = self.contract_id.sueldo_diario_integrado * self.imss_dias
        uma3 =  self.contract_id.tablas_cfdi_id.uma * 3
        # falta especie excedente

        self.prestaciones = salario_cotizado * self.contract_id.tablas_cfdi_id.enf_mat_prestaciones_e/100
        self.invalli_y_vida = salario_cotizado * self.contract_id.tablas_cfdi_id.inv_vida_e/100
        self.cesantia_y_vejez = salario_cotizado * self.contract_id.tablas_cfdi_id.cesantia_vejez_e/100
        self.pensio_y_benefi = salario_cotizado * self.contract_id.tablas_cfdi_id.enf_mat_gastos_med_e/100

        #seguro_enfermedad_maternidad
        excedente = self.contract_id.sueldo_diario_integrado - uma3
        base_cotizacion = excedente * self.imss_mes
        seg_enf_mat = base_cotizacion * self.contract_id.tablas_cfdi_id.enf_mat_excedente_e/100

        if self.contract_id.sueldo_diario_integrado < uma3:
            self.prestaciones = self.prestaciones + self.pensio_y_benefi
        else:
            self.prestaciones = self.prestaciones + self.pensio_y_benefi + abs(seg_enf_mat)

class HrPayslipMail(models.Model):
    _name = "hr.payslip.mail"
    _inherit = ['mail.thread']
    _description = "Nomina Mail"
   
    payslip_id = fields.Many2one('hr.payslip', string='Nomina')
    name = fields.Char(related='payslip_id.name')
    xml_nomina_link = fields.Char(related='payslip_id.xml_nomina_link')
    employee_id = fields.Many2one(related='payslip_id.employee_id')
    company_id = fields.Many2one(related='payslip_id.company_id')
    
class MailTemplate(models.Model):
    "Templates for sending email"
    _inherit = 'mail.template'
    
    @api.model
    def _get_file(self, url):
        url = url.encode('utf8')
        filename, headers = urllib.urlretrieve(url)
        fn, file_extension = os.path.splitext(filename)
        return  filename, file_extension.replace('.', '')

    @api.multi
    def generate_email(self, res_ids, fields=None):
        results = super(MailTemplate, self).generate_email(res_ids, fields=fields)
        
        if isinstance(res_ids, (int)):
            res_ids = [res_ids]
        res_ids_to_templates = super(MailTemplate, self).get_email_template(res_ids)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.items():
            templates_to_res_ids.setdefault(template, []).append(res_id)
        
        template_id = self.env.ref('nomina_cfdi.email_template_payroll')
        for template, template_res_ids in templates_to_res_ids.items():
            if template.id  == template_id.id:
                for res_id in template_res_ids:
                    payment = self.env[template.model].browse(res_id)
                    if payment.xml_nomina_link:
                        attachments =  results[res_id]['attachments'] or []
                        names = payment.xml_nomina_link.split('/')
                        fn = names[len(names) - 1]
                        data = open(payment.xml_nomina_link, 'rb').read()
                        attachments.append((fn, base64.b64encode(data)))
                        results[res_id]['attachments'] = attachments
        return results

