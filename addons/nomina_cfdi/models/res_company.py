# -*- coding: utf-8 -*-
import base64
import json
import requests
from odoo import fields, models,api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class ResCompany(models.Model):
    _inherit = 'res.company'

    rfc_patron = fields.Char(string=_('RFC Patrón'))
    serie_nomina = fields.Char(string=_('Serie nomina'))
    registro_patronal = fields.Char(string=_('Registro patronal'))
    #nomina_mail = fields.Many2one("mail.template", 'Nomina Mail',)
    nomina_mail = fields.Char('Nomina Mail',)
    
    @api.model
    def contract_warning_mail_cron(self):
        companies = self.search([('nomina_mail','!=',False)])
        cr = self._cr
        dt = datetime.now()
        start_week_day = (dt - timedelta(days=dt.weekday())).date()
        end_week_day = start_week_day + timedelta(days=6)
        
        where_clause = []
        while start_week_day<=end_week_day:
            where_clause.append("TO_CHAR(date_start,'MM-DD')='%s-%s'"%("{0:0=2d}".format(start_week_day.month),"{0:0=2d}".format(start_week_day.day)))
            start_week_day = start_week_day + timedelta(days=1) #.date()
        where_clause = " OR ".join(where_clause)
        
        for company in companies:
            cr.execute("select id from hr_contract where (%s) and company_id=%d"%(where_clause,company.id))
            contract_ids = [r[0] for r in cr.fetchall()]
            if not contract_ids:
                continue
            for contract in self.env['hr.contract'].browse(contract_ids):
                #self.env['hr.contract'].browse(contract_ids)
                if not contract.employee_id.work_email:
                    continue
                
                mail_values = {
                    #'email_from': contract.employee_id.work_email,
                    #'reply_to': mailing.reply_to,
                    'email_to': company.nomina_mail,
                    'subject': '',
                    'body_html': 'Esta semana cumpleaños ' +  contract.employee_id.name + ' en la empresa, revisar ajuste en sueldo diario integrado.',
                    'notification': True,
                    #'mailing_id': mailing.id,
                    #'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                    'auto_delete': True,
                }
                mail = self.env['mail.mail'].create(mail_values)
                mail.send()
                self.calculate_contract_vacaciones(contract)
                #self.calculate_sueldo_diario_integrado(contract)
                #company.nomina_mail.send_mail(contract_id, force_send=True )
        return
    
    @api.model
    def calculate_contract_vacaciones(self, contract):
        tablas_cfdi = contract.tablas_cfdi_id
        if not tablas_cfdi:
            tablas_cfdi = self.env['tablas.cfdi'].search([],limit=1)
        if not tablas_cfdi:
            return
        antiguedad_anos = contract.antiguedad_anos
        if antiguedad_anos < 1.0:
            tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad >= antiguedad_anos).sorted(key=lambda x:x.antiguedad)
        else:
            tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad <= antiguedad_anos).sorted(key=lambda x:x.antiguedad, reverse=True)
        if not tablas_cfdi_lines:
            return
        tablas_cfdi_line = tablas_cfdi_lines[0]
        today = datetime.today()
        current_year = today.strftime('%Y')
        contract.write({'tabla_vacaciones': [(0, 0, {'ano':current_year, 'dias': tablas_cfdi_line.vacaciones})]})
        return True
    
    @api.model
    def calculate_sueldo_diario_integrado(self, contract):
        if contract.date_start:
            today = datetime.today().date()
            diff_date = (today - contract.date_start + timedelta(days=1)).days #today - date_start 
            years = diff_date /365.0
            tablas_cfdi = contract.tablas_cfdi_id
            if not tablas_cfdi:
                tablas_cfdi = self.env['tablas.cfdi'].search([],limit=1)
            if not tablas_cfdi:
                return
            if years < 1.0:
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad >= years).sorted(key=lambda x:x.antiguedad)
            else:
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad <= years).sorted(key=lambda x:x.antiguedad, reverse=True)
            if not tablas_cfdi_lines:
                return
            tablas_cfdi_line = tablas_cfdi_lines[0]
            sueldo_diario_integrado = ((365 + tablas_cfdi_line.aguinaldo + (tablas_cfdi_line.vacaciones)* (tablas_cfdi_line.prima_vac/100) ) / 365) * contract.wage/30
            if sueldo_diario_integrado > (tablas_cfdi.uma * 25):
                sueldo_diario_integrado = tablas_cfdi.uma * 25
            contract.write({'sueldo_diario_integrado': sueldo_diario_integrado})
        return
