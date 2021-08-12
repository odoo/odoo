# -*- coding: utf-8 -*-

import base64
import json
import requests
from odoo import fields, models,api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class ResCompany(models.Model):
    _inherit = 'res.company'

    rfc = fields.Char(string=_('RFC'))
    proveedor_timbrado= fields.Selection(
        selection=[('multifactura', _('Servidor 1')),
                   ('gecoerp', _('Servidor 2')),
                   ('multifactura2', _('Servidor 3')),
                   ('multifactura3', _('Servidor 4')),],
        string=_('Proveedor de timbrado'), 
    )
    api_key = fields.Char(string=_('API Key'))
    http_factura = fields.Char(string=_('HTTP Factura'))
    factura_dir = fields.Char(string=_('Directorio XML'))
    modo_prueba = fields.Boolean(string=_('Modo prueba'))
    serie_factura = fields.Char(string=_('Serie factura'))
    regimen_fiscal = fields.Selection(
        selection=[('601', _('General de Ley Personas Morales')),
                   ('603', _('Personas Morales con Fines no Lucrativos')),
                   ('605', _('Sueldos y Salarios e Ingresos Asimilados a Salarios')),
                   ('606', _('Arrendamiento')),
                   ('608', _('Demás ingresos')),
                   ('609', _('Consolidación')),
                   ('610', _('Residentes en el Extranjero sin Establecimiento Permanente en México')),
                   ('611', _('Ingresos por Dividendos (socios y accionistas)')),
                   ('612', _('Personas Físicas con Actividades Empresariales y Profesionales')),
                   ('614', _('Ingresos por intereses')),
                   ('616', _('Sin obligaciones fiscales')),
                   ('620', _('Sociedades Cooperativas de Producción que optan por diferir sus ingresos')),
                   ('621', _('Incorporación Fiscal')),
                   ('622', _('Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras')),
                   ('623', _('Opcional para Grupos de Sociedades')),
                   ('624', _('Coordinados')),
                   ('628', _('Hidrocarburos')),
                   ('607', _('Régimen de Enajenación o Adquisición de Bienes')),
                   ('629', _('De los Regímenes Fiscales Preferentes y de las Empresas Multinacionales')),
                   ('630', _('Enajenación de acciones en bolsa de valores')),
                   ('615', _('Régimen de los ingresos por obtención de premios')),
                   ('625', _('Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas')),],
        string=_('Régimen Fiscal'), 
    )
    archivo_cer = fields.Binary(string=_('Archivo .cer'))
    archivo_key = fields.Binary(string=_('Archivo .key'))
    contrasena = fields.Char(string=_('Contraseña'))
    nombre_fiscal = fields.Char(string=_('Razón social'))
    serie_complemento = fields.Char(string=_('Serie complemento de pago'))
    telefono_sms = fields.Char(string=_('Teléfono celular'))  
    saldo_timbres =  fields.Float(string=_('Saldo de timbres'), readonly=True)
    saldo_alarma =  fields.Float(string=_('Alarma timbres'), default=10)
    correo_alarma =  fields.Char(string=_('Correo de alarma'))
    fecha_csd = fields.Datetime(string=_('Vigencia CSD'), readonly=True)
    estado_csd =  fields.Char(string=_('Estado CSD'), readonly=True)
    aviso_csd =  fields.Char(string=_('Aviso vencimiento (días antes)'), default=14)

    @api.model
    def get_saldo_by_cron(self):
        companies = self.search([('proveedor_timbrado','!=',False)])
        for company in companies:
            company.get_saldo()
            if company.saldo_timbres < company.saldo_alarma and company.correo_alarma: #valida saldo de timbres
                email_template = self.env.ref("cdfi_invoice.email_template_alarma_de_saldo",False)
                if not email_template:return
                emails = company.correo_alarma.split(",")
                for email in emails:
                    email = email.strip()
                    if email:
                        email_template.send_mail(company.id, force_send=True,email_values={'email_to':email})
            if company.aviso_csd and company.fecha_csd and company.correo_alarma: #valida vigencia de CSD
                if datetime.today() + timedelta(days=1) > company.fecha_csd: 
                   email_template = self.env.ref("cdfi_invoice.email_template_alarma_de_csd",False)
                   if not email_template:return
                   emails = company.correo_alarma.split(",")
                   for email in emails:
                       email = email.strip()
                       if email:
                          email_template.send_mail(company.id, force_send=True,email_values={'email_to':email})
        return True

    def get_saldo(self):
        values = {
                 'rfc': self.rfc,
                 'api_key': self.proveedor_timbrado,
                 'modo_prueba': self.modo_prueba,
                 }
        url=''
        if self.proveedor_timbrado == 'multifactura':
            url = '%s' % ('http://facturacion.itadmin.com.mx/api/saldo')
        elif self.proveedor_timbrado == 'gecoerp':
            if self.modo_prueba:
                #url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/invoice/?handler=OdooHandler33')
                url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
            else:
                url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
        if not url:
            return
        try:
            response = requests.post(url,auth=None,verify=False, data=json.dumps(values),headers={"Content-type": "application/json"})
            json_response = response.json()
        except Exception as e:
            print(e)
            json_response = {}
    
        if not json_response:
            return
        
        estado_factura = json_response['estado_saldo']
        if estado_factura == 'problemas_saldo':
            raise UserError(_(json_response['problemas_message']))
        if json_response.get('saldo'):
            xml_saldo = base64.b64decode(json_response['saldo'])
        values2 = {
                    'saldo_timbres': xml_saldo
                  }
        self.update(values2)

    def validar_csd(self):
        values = {
                 'rfc': self.rfc,
                 'archivo_cer': self.archivo_cer.decode("utf-8"),
                 'archivo_key': self.archivo_key.decode("utf-8"),
                 'contrasena': self.contrasena,
                 }
        url=''
        if self.proveedor_timbrado == 'multifactura':
            url = '%s' % ('http://facturacion.itadmin.com.mx/api/validarcsd')
        elif self.proveedor_timbrado == 'multifactura2':
            url = '%s' % ('http://facturacion2.itadmin.com.mx/api/validarcsd')
        elif self.proveedor_timbrado == 'multifactura3':
            url = '%s' % ('http://facturacion3.itadmin.com.mx/api/validarcsd')
        if not url:
            return
        try:
            response = requests.post(url,auth=None,verify=False, data=json.dumps(values),headers={"Content-type": "application/json"})
            json_response = response.json()
        except Exception as e:
            print(e)
            json_response = {}

        if not json_response:
            return
        #_logger.info('something ... %s', response.text)

        respuesta = json_response['respuesta']
        if json_response['respuesta'] == 'Certificados CSD correctos':
           self.fecha_csd = datetime.strptime(json_response['fecha'], '%d-%b-%Y %H:%M:%S')  # 17-Jun-2023 20:40:51
           values2 = {
               'fecha_csd': self.fecha_csd,
               'estado_csd': json_response['respuesta'],
               }
           self.update(values2)
        else:
           raise UserError(respuesta)

    def borrar_csd(self):
        values = {
                 'rfc': self.rfc,
                 }
        url=''
        if self.proveedor_timbrado == 'multifactura':
            url = '%s' % ('http://facturacion.itadmin.com.mx/api/borrarcsd')
        elif self.proveedor_timbrado == 'multifactura2':
            url = '%s' % ('http://facturacion2.itadmin.com.mx/api/borrarcsd')
        elif self.proveedor_timbrado == 'multifactura3':
            url = '%s' % ('http://facturacion3.itadmin.com.mx/api/borrarcsd')
        if not url:
            return
        try:
            response = requests.post(url,auth=None,verify=False, data=json.dumps(values),headers={"Content-type": "application/json"})
            json_response = response.json()
        except Exception as e:
            print(e)
            json_response = {}

        if not json_response:
            return
        #_logger.info('something ... %s', response.text)
        respuesta = json_response['respuesta']
        raise UserError(respuesta)

    def borrar_estado(self):
           values2 = {
               'fecha_csd': '',
               'estado_csd': '',
               }
           self.update(values2)

    @api.multi
    def button_dummy(self):
        self.get_saldo()
        return True
