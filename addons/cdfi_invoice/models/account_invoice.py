# -*- coding: utf-8 -*-

import base64
import json
import requests
import datetime
from lxml import etree

from odoo import fields, models, api,_ 
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, Warning

from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.units import mm
from . import amount_to_text_es_MX
import pytz
from .tzlocal import get_localzone
from odoo import tools

import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    factura_cfdi = fields.Boolean('Factura CFDI')
    tipo_comprobante = fields.Selection(
        selection=[('I', 'Ingreso'), 
                   ('E', 'Egreso'),
                   ('T', 'Traslado')
                  ],
        string=_('Tipo de comprobante'),
    )
    forma_pago = fields.Selection(
        selection=[('01', '01 - Efectivo'), 
                   ('02', '02 - Cheque nominativo'), 
                   ('03', '03 - Transferencia electrónica de fondos'),
                   ('04', '04 - Tarjeta de Crédito'), 
                   ('05', '05 - Monedero electrónico'),
                   ('06', '06 - Dinero electrónico'), 
                   ('08', '08 - Vales de despensa'), 
                   ('12', '12 - Dación en pago'), 
                   ('13', '13 - Pago por subrogación'), 
                   ('14', '14 - Pago por consignación'), 
                   ('15', '15 - Condonación'), 
                   ('17', '17 - Compensación'), 
                   ('23', '23 - Novación'), 
                   ('24', '24 - Confusión'), 
                   ('25', '25 - Remisión de deuda'), 
                   ('26', '26 - Prescripción o caducidad'), 
                   ('27', '27 - A satisfacción del acreedor'), 
                   ('28', '28 - Tarjeta de débito'), 
                   ('29', '29 - Tarjeta de servicios'), 
                   ('30', '30 - Aplicación de anticipos'), 
                   ('31', '31 - Intermediario pagos'),
                   ('99', '99 - Por definir'),],
        string=_('Forma de pago'),
    )
    methodo_pago = fields.Selection(
        selection=[('PUE', _('Pago en una sola exhibición')),
				   ('PPD', _('Pago en parcialidades o diferido')),],
        string=_('Método de pago'), 
    )
    uso_cfdi = fields.Selection(
        selection=[('G01', _('Adquisición de mercancías')),
                   ('G02', _('Devoluciones, descuentos o bonificaciones')),
                   ('G03', _('Gastos en general')),
                   ('I01', _('Construcciones')),
                   ('I02', _('Mobiliario y equipo de oficina por inversiones')),
                   ('I03', _('Equipo de transporte')),
                   ('I04', _('Equipo de cómputo y accesorios')),
                   ('I05', _('Dados, troqueles, moldes, matrices y herramental')),
                   ('I06', _('Comunicacion telefónica')),
                   ('I07', _('Comunicación Satelital')),
                   ('I08', _('Otra maquinaria y equipo')),
                   ('D01', _('Honorarios médicos, dentales y gastos hospitalarios')),
                   ('D02', _('Gastos médicos por incapacidad o discapacidad')),
                   ('D03', _('Gastos funerales')),
                   ('D04', _('Donativos')),
                   ('D07', _('Primas por seguros de gastos médicos')),
                   ('D08', _('Gastos de transportación escolar obligatoria')),
                   ('D10', _('Pagos por servicios educativos (colegiaturas)')),
                   ('P01', _('Por definir')),],
        string=_('Uso CFDI (cliente)'),
    )
    xml_invoice_link = fields.Char(string=_('XML Invoice Link'))
    estado_factura = fields.Selection(
        selection=[('factura_no_generada', 'Factura no generada'), ('factura_correcta', 'Factura correcta'), 
                   ('solicitud_cancelar', 'Cancelación en proceso'),('factura_cancelada', 'Factura cancelada'),
                   ('solicitud_rechazada', 'Cancelación rechazada'),],
        string=_('Estado de factura'),
        default='factura_no_generada',
        readonly=True
    )
    pdf_cdfi_invoice = fields.Binary("CDFI Invoice")
    qrcode_image = fields.Binary("QRCode")
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
                   ('615', _('Régimen de los ingresos por obtención de premios')),],
        string=_('Régimen Fiscal'), 
    )
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
    number_folio = fields.Char(string=_('Folio'), compute='_get_number_folio')
    amount_to_text = fields.Char('Amount to Text', compute='_get_amount_to_text',
                                 size=256, 
                                 help='Amount of the invoice in letter')
    qr_value = fields.Char(string=_('QR Code Value'))
    invoice_datetime = fields.Char(string=_('11/12/17 12:34:12'))
    fecha_factura = fields.Datetime(string=_('Fecha Factura'), readonly=True)
    rfc_emisor = fields.Char(string=_('RFC'))
    name_emisor = fields.Char(string=_('Name'))
    serie_emisor = fields.Char(string=_('A'))
    tipo_relacion = fields.Selection(
        selection=[('01', 'Nota de crédito de los documentos relacionados'), 
                   ('02', 'Nota de débito de los documentos relacionados'), 
                   ('03', 'Devolución de mercancía sobre facturas o traslados previos'),
                   ('04', 'Sustitución de los CFDI previos'), 
                   ('05', 'Traslados de mercancías facturados previamente'),
                   ('06', 'Factura generada por los traslados previos'), 
                   ('07', 'CFDI por aplicación de anticipo'),],
        string=_('Tipo relación'),
    )
    uuid_relacionado = fields.Char(string=_('CFDI Relacionado'))
    confirmacion = fields.Char(string=_('Confirmación'))
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Product Price'))
    monto = fields.Float(string='Amount', digits=dp.get_precision('Product Price'))
    precio_unitario = fields.Float(string='Precio unitario', digits=dp.get_precision('Product Price'))
    monto_impuesto = fields.Float(string='Monto impuesto', digits=dp.get_precision('Product Price'))
    total_impuesto = fields.Float(string='Monto impuesto', digits=dp.get_precision('Product Price'))
    decimales = fields.Float(string='decimales')
    desc = fields.Float(string='descuento', digits=dp.get_precision('Product Price'))
    subtotal = fields.Float(string='subtotal', digits=dp.get_precision('Product Price'))
    total = fields.Float(string='total', digits=dp.get_precision('Product Price'))

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice=date_invoice, 
                                                           date=date, description=description, journal_id=journal_id)
        if invoice.estado_factura == 'factura_correcta':
            values['uuid_relacionado'] = invoice.folio_fiscal
            values['methodo_pago'] = invoice.methodo_pago
            values['forma_pago'] = invoice.forma_pago
            values['tipo_comprobante'] = 'E'
            values['uso_cfdi'] = 'G02'
            values['tipo_relacion'] = '01'
            values['fecha_factura'] = None
        return values


    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if self.estado_factura == 'factura_correcta' or self.estado_factura == 'factura_cancelada':
            default['estado_factura'] = 'factura_no_generada'
            default['folio_fiscal'] = ''
            default['fecha_factura'] = None
            default['factura_cfdi'] = False
        return super(AccountInvoice, self).copy(default=default)
    
    @api.depends('number')
    @api.one
    def _get_number_folio(self):
        if self.number:
            self.number_folio = self.number.replace('INV','').replace('/','')
            
    @api.depends('amount_total', 'currency_id')
    @api.one
    def _get_amount_to_text(self):
        self.amount_to_text = amount_to_text_es_MX.get_amount_to_text(self, self.amount_total, 'es_cheque', self.currency_id.name)
        
    @api.model
    def _get_amount_2_text(self, amount_total):
        return amount_to_text_es_MX.get_amount_to_text(self, amount_total, 'es_cheque', self.currency_id.name)

    @api.multi
    @api.onchange('partner_id')
    def _get_uso_cfdi(self):
        if self.partner_id:
            values = {
                'uso_cfdi': self.partner_id.uso_cfdi
                }
            self.update(values)

    @api.multi
    @api.onchange('payment_term_id')
    def _get_metodo_pago(self):
        if self.payment_term_id:
            if self.payment_term_id.methodo_pago == 'PPD':
                values = {
                 'methodo_pago': self.payment_term_id.methodo_pago,
                 'forma_pago': '99'
                }
            else:
                values = {
                    'methodo_pago': self.payment_term_id.methodo_pago,
                    'forma_pago': False
                    }
        else:
            values = {
                'methodo_pago': False,
                'forma_pago': False
                }
        self.update(values)
    
    @api.model
    def to_json(self):
        if self.partner_id.name == 'Factura global CFDI 33':
            nombre = ''
        else:
            nombre = self.partner_id.name
        decimales = self.env['decimal.precision'].search([('name','=','Product Price')])
        no_decimales = decimales.digits

        #corregir hora
        timezone = self._context.get('tz')
        if not timezone:
            timezone = self.journal_id.tz or self.env.user.partner_id.tz or 'America/Mexico_City'
        #timezone = tools.ustr(timezone).encode('utf-8')

        local = pytz.timezone(timezone)
        naive_from = datetime.datetime.now() 
        local_dt_from = naive_from.replace(tzinfo=pytz.UTC).astimezone(local)
        date_from = local_dt_from.strftime ("%Y-%m-%d %H:%M:%S")

        _logger.info('date_from %s', date_from)
        request_params = { 
                'company': {
                      'rfc': self.company_id.rfc,
                      'api_key': self.company_id.proveedor_timbrado,
                      'modo_prueba': self.company_id.modo_prueba,
                      'regimen_fiscal': self.company_id.regimen_fiscal,
                      'postalcode': self.journal_id.codigo_postal or self.company_id.zip,
                      'nombre_fiscal': self.company_id.nombre_fiscal,
                      'telefono_sms': self.company_id.telefono_sms,
                },
                'customer': {
                      'name': nombre,
                      'rfc': self.partner_id.rfc,
                      'residencia_fiscal': self.partner_id.residencia_fiscal,
                      'registro_tributario': self.partner_id.registro_tributario,
                      'uso_cfdi': self.uso_cfdi,
                },
                'invoice': {
                      'tipo_comprobante': self.tipo_comprobante,
                      'moneda': self.currency_id.name,
                      'tipocambio': self.currency_id.rate,
                      'forma_pago': self.forma_pago,
                      'methodo_pago': self.methodo_pago,
                      'subtotal': self.amount_untaxed,
                      'total': self.amount_total,
                      'folio': self.number.replace('INV','').replace('/',''),
                      'serie_factura': self.journal_id.serie_diario or self.company_id.serie_factura,
                      'fecha_factura': date_from, #self.fecha_factura,
                      'decimales_cantidad': 6,
                },
                'adicional': {
                      'tipo_relacion': self.tipo_relacion,
                      'uuid_relacionado': self.uuid_relacionado,
                      'confirmacion': self.confirmacion,
                },
                'version': {
                      'cfdi': '3.3',
                      'sistema': 'odoo12',
                      'version': '6',
                },
        }
        amount_total = 0.0
        amount_untaxed = 0.0
        self.subtotal = 0
        self.total = 0
        self.discount = 0
        tax_grouped = {}
        items = {'numerodepartidas': len(self.invoice_line_ids)}
        invoice_lines = []
        for line in self.invoice_line_ids:
            if line.quantity <= 0:
                continue
            self.total_impuesto = 0.0
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            amounts = line.invoice_line_tax_ids.compute_all(price, line.currency_id, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            _logger.info('amounts %s', amounts)
            price_exclude_tax = amounts['total_excluded']
            price_include_tax = amounts['total_included']
            if line.invoice_id:
                price_exclude_tax = line.invoice_id.currency_id.round(price_exclude_tax)
                price_include_tax = line.invoice_id.currency_id.round(price_include_tax)
            amount_total += price_include_tax
            taxes = amounts['taxes']
            tax_items = []
            amount_wo_tax = line.price_unit * line.quantity
            product_taxes = {'numerodeimpuestos': len(taxes)}
            for tax in taxes:
                tax_id = self.env['account.tax'].browse(tax['id'])
                if tax_id.price_include or tax_id.amount_type == 'division':
                    amount_wo_tax -= float("%.2f" % tax['amount'])
                self.monto_impuesto = float("%.2f" % tax['amount'])
                self.total_impuesto += self.monto_impuesto
                _logger.info('monto_impuesto %s', self.monto_impuesto)
                tax_items.append({'name': tax_id.tax_group_id.name,
                 'percentage': tax_id.amount,
                 'amount': self.monto_impuesto,
                 'impuesto': tax_id.impuesto,
                 'tipo_factor': tax_id.tipo_factor,
                 'nombre': tax_id.impuesto_local,})
                val = {'invoice_id': line.invoice_id.id,
                 'name': tax_id.tax_group_id.name,
                 'tax_id': tax['id'],
                 'amount': float("%.2f" % tax['amount'])}
                key = tax['id']
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
            if tax_items:
                product_taxes.update({'tax_lines': tax_items})

            self.precio_unitario = "{:.2f}".format(float(amount_wo_tax) / float(line.quantity))
            self.monto = line.price_subtotal #self.precio_unitario * line.quantity
            amount_untaxed += self.monto
            self.subtotal += self.monto
            self.total += self.monto + self.total_impuesto

            if line.discount > 0:
               self.desc = "{:.2f}".format(self.precio_unitario * line.quantity - line.price_subtotal)
            else:
                self.desc = 0
            _logger.info('descuento_b %s', self.desc)
            self.discount += self.desc
            _logger.info('descuento %s', self.discount)

            product_string = line.product_id.code and line.product_id.code[:100] or ''
            if product_string == '':
               if line.name.find(']') > 0:
                  product_string = line.name[line.name.find('[')+len('['):line.name.find(']')] or ''

            #self.amount = p_unit * line.quantity * (1 - (line.discount or 0.0) / 100.0)
            if self.tipo_comprobante == 'E':
                invoice_lines.append({'quantity': line.quantity,
                                      'unidad_medida': line.product_id.unidad_medida,
                                      'product': product_string,
                                      'price_unit': self.precio_unitario,
                                      'amount': "{:.2f}".format(self.monto + self.desc),
                                      'description': line.name[:1000],
                                      'clave_producto': '84111506',
                                      'clave_unidad': 'ACT',
                                      'taxes': product_taxes,
                                      'descuento': self.desc,
                                      'numero_pedimento': line.pedimento,
                                      'numero_predial': line.predial})
            elif self.tipo_comprobante == 'T':
                invoice_lines.append({'quantity': line.quantity,
                                      'unidad_medida': line.product_id.unidad_medida,
                                      'product': product_string,
                                      'price_unit': self.precio_unitario,
                                      'amount': "{:.2f}".format(self.monto + self.desc),
                                      'description': line.name[:1000],
                                      'clave_producto': line.product_id.clave_producto,
                                      'clave_unidad': line.product_id.clave_unidad})
            else:
                invoice_lines.append({'quantity': line.quantity,
                                      'unidad_medida': line.product_id.unidad_medida,
                                      'product': product_string,
                                      'price_unit': self.precio_unitario,
                                      'amount': "{:.2f}".format(self.monto + self.desc),
                                      'description': line.name[:1000],
                                      'clave_producto': line.product_id.clave_producto,
                                      'clave_unidad': line.product_id.clave_unidad,
                                      'taxes': product_taxes,
                                      'descuento': self.desc,
                                      'numero_pedimento': line.pedimento,
                                      'numero_predial': line.predial})


        self.discount = round(self.discount,2)
        if self.tipo_comprobante == 'T':
            request_params['invoice'].update({'subtotal': '0.00','total': '0.00'})
        else:
            request_params['invoice'].update({'subtotal': "{:.2f}".format(self.subtotal  + self.discount),'total': "{:.2f}".format(self.total)})
        items.update({'invoice_lines': invoice_lines})
        request_params.update({'items': items})
        tax_lines = []
        tax_count = 0
        for line in tax_grouped.values():
            tax_count += 1
            tax = self.env['account.tax'].browse(line['tax_id'])
            tax_lines.append({
                      'name': line['name'],
                      'percentage': tax.amount,
                      'amount': float("%.2f" % line['amount']),
                })
        taxes = {'numerodeimpuestos': tax_count}
        if tax_lines:
            taxes.update({'tax_lines': tax_lines})
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
    def invoice_validate(self):
        # after validate, send invoice data to external system via http post
        for invoice in self:
            if invoice.factura_cfdi:
                if invoice.fecha_factura == False:
                    invoice.fecha_factura= datetime.datetime.now()
                    invoice.write({'fecha_factura': invoice.fecha_factura})
                if invoice.estado_factura == 'factura_correcta' and invoice.state == 'draft':
                    continue
                if invoice.estado_factura == 'factura_correcta' and invoice.state != 'draft':
                    raise UserError(_('Error para validar factura, Factura ya generada.'))
                if invoice.estado_factura == 'factura_cancelada':
                    raise UserError(_('Error para validar factura, Factura ya generada y cancelada.'))
                values = invoice.to_json()
                url=''
                if invoice.company_id.proveedor_timbrado == 'multifactura':
                    url = '%s' % ('http://facturacion.itadmin.com.mx/api/invoice')
                elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                    url = '%s' % ('http://facturacion2.itadmin.com.mx/api/invoice')
                elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                    url = '%s' % ('http://facturacion3.itadmin.com.mx/api/invoice')
                elif invoice.company_id.proveedor_timbrado == 'gecoerp':
                    if self.company_id.modo_prueba:
                        #url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/invoice/?handler=OdooHandler33')
                        url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
                    else:
                        url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
                try:
                    response = requests.post(url , 
                                         auth=None,verify=False, data=json.dumps(values), 
                                         headers={"Content-type": "application/json"})
                except Exception as e:
                    error = str(e)
                    if "Name or service not known" in error or "Failed to establish a new connection" in error:
                        raise Warning("Servidor fuera de servicio, favor de intentar mas tarde")
                    else:
                        raise Warning(error)
    
                #_logger.info('something ... %s', response.text)
                json_response = response.json()
                xml_file_link = False
                estado_factura = json_response['estado_factura']
                if estado_factura == 'problemas_factura':
                    raise UserError(_(json_response['problemas_message']))
                # Receive and stroe XML invoice
                if json_response.get('factura_xml'):
                    xml_file_link = invoice.company_id.factura_dir + '/' + invoice.number.replace('/', '_') + '.xml'
                    xml_file = open(xml_file_link, 'w')
                    xml_invoice = base64.b64decode(json_response['factura_xml'])
                    xml_file.write(xml_invoice.decode("utf-8"))
                    xml_file.close()
                    invoice._set_data_from_xml(xml_invoice)
                    
                    file_name = invoice.number.replace('/', '_') + '.xml'
                    self.env['ir.attachment'].sudo().create(
                                                {
                                                    'name': file_name,
                                                    'datas': json_response['factura_xml'],
                                                    'datas_fname': file_name,
                                                    'res_model': self._name,
                                                    'res_id': invoice.id,
                                                    'type': 'binary'
                                                })
                invoice.write({'estado_factura': estado_factura,
                               'xml_invoice_link': xml_file_link})
                invoice.message_post(body="CFDI emitido")
        result = super(AccountInvoice, self).invoice_validate()
        return result
    
    @api.multi
    def generate_cfdi_invoice(self):
        # after validate, send invoice data to external system via http post
        for invoice in self:
            if self.estado_factura == 'factura_correcta':
                raise UserError(_('Error para timbrar factura, Factura ya generada.'))
            if self.estado_factura == 'factura_cancelada':
                raise UserError(_('Error para timbrar factura, Factura ya generada y cancelada.'))
            self.fecha_factura= datetime.datetime.now()
            values = invoice.to_json()
            if self.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % ('http://facturacion2.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % ('http://facturacion3.itadmin.com.mx/api/invoice')
            elif self.company_id.proveedor_timbrado == 'gecoerp':
                url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
            try:
                response = requests.post(url , 
                                         auth=None,verify=False, data=json.dumps(values), 
                                         headers={"Content-type": "application/json"})
            except Exception as e:
                error = str(e)
                if "Name or service not known" in error or "Failed to establish a new connection" in error:
                    raise Warning("Servidor fuera de servicio, favor de intentar mas tarde")
                else:
                    raise Warning(error)

            #_logger.info('something ... %s', response.text)
            json_response = response.json()
            xml_file_link = False
            estado_factura = json_response['estado_factura']
            if estado_factura == 'problemas_factura':
                raise UserError(_(json_response['problemas_message']))
            # Receive and stroe XML invoice
            if json_response.get('factura_xml'):
                xml_file_link = invoice.company_id.factura_dir + '/' + invoice.number.replace('/', '_') + '.xml'
                xml_file = open(xml_file_link, 'w')
                xml_invoice = base64.b64decode(json_response['factura_xml'])
                xml_file.write(xml_invoice.decode("utf-8"))
                xml_file.close()
                invoice._set_data_from_xml(xml_invoice)
            invoice.write({'estado_factura': estado_factura,
                           'xml_invoice_link': xml_file_link,
                           'factura_cfdi': True})
            invoice.message_post(body="CFDI emitido")
        return True
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
        #self.methodo_pago = xml_data.attrib['MetodoPago']
        #self.forma_pago = _(xml_data.attrib['FormaPago'])
        #  self.condicione_pago = xml_data.attrib['condicionesDePago']
        #self.num_cta_pago = xml_data.get('NumCtaPago', '')
        self.tipocambio = xml_data.attrib['TipoCambio']
        self.tipo_comprobante = xml_data.attrib['TipoDeComprobante']
        self.moneda = xml_data.attrib['Moneda']
        self.regimen_fiscal = Emisor.attrib['RegimenFiscal'] #checar este!!
        self.numero_cetificado = xml_data.attrib['NoCertificado']
        self.cetificaso_sat = TimbreFiscalDigital.attrib['NoCertificadoSAT']
        self.fecha_certificacion = TimbreFiscalDigital.attrib['FechaTimbrado']
        self.selo_digital_cdfi = TimbreFiscalDigital.attrib['SelloCFD']
        self.selo_sat = TimbreFiscalDigital.attrib['SelloSAT']
        self.folio_fiscal = TimbreFiscalDigital.attrib['UUID']
        self.folio = xml_data.attrib['Folio']
        if self.company_id.serie_factura:
           self.serie_emisor = xml_data.attrib['Serie']
        self.invoice_datetime = xml_data.attrib['Fecha']
        self.version = TimbreFiscalDigital.attrib['Version']
        self.cadena_origenal = '||%s|%s|%s|%s|%s||' % (self.version, self.folio_fiscal, self.fecha_certificacion, 
                                                         self.selo_digital_cdfi, self.cetificaso_sat)
        
        options = {'width': 275 * mm, 'height': 275 * mm}
        amount_str = str(self.amount_total).split('.')
        qr_value = 'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?&id=%s&re=%s&rr=%s&tt=%s.%s&fe=%s' % (self.folio_fiscal,
                                                 self.company_id.rfc, 
                                                 self.partner_id.rfc,
                                                 amount_str[0].zfill(10),
                                                 amount_str[1].ljust(6, '0'),
                                                 self.selo_digital_cdfi[-8:],
                                                 )
        self.qr_value = qr_value
        ret_val = createBarcodeDrawing('QR', value=qr_value, **options)
        self.qrcode_image = base64.encodestring(ret_val.asString('jpg'))
    
    @api.multi
    def print_cdfi_invoice(self):
        self.ensure_one()
        #return self.env['report'].get_action(self, 'custom_invoice.cdfi_invoice_report') #modulename.custom_report_coupon 
        filename = 'CDFI_' + self.number.replace('/', '_') + '.pdf'
        return {
                 'type' : 'ir.actions.act_url',
                 'url': '/web/binary/download_document?model=account.invoice&field=pdf_cdfi_invoice&id=%s&filename=%s'%(self.id, filename),
                 'target': 'self',
                 }
        
    @api.multi
    def action_cfdi_generate(self):
        # after validate, send invoice data to external system via http post
        for invoice in self:
            if invoice.fecha_factura == False:
                invoice.fecha_factura= datetime.datetime.now()
                invoice.write({'fecha_factura': invoice.fecha_factura})
            if invoice.estado_factura == 'factura_correcta':
                if invoice.folio_fiscal:
                    invoice.write({'factura_cfdi': True})
                    return True
                else:
                    raise UserError(_('Error para timbrar factura, Factura ya generada.'))
            if invoice.estado_factura == 'factura_cancelada':
                raise UserError(_('Error para timbrar factura, Factura ya generada y cancelada.'))
            
            values = invoice.to_json()
            if invoice.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % ('http://facturacion2.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % ('http://facturacion3.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'gecoerp':
                if self.company_id.modo_prueba:
                    #url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/invoice/?handler=OdooHandler33')
                    url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
                else:
                    url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
            try:
                response = requests.post(url , 
                                         auth=None,verify=False, data=json.dumps(values), 
                                         headers={"Content-type": "application/json"})
            except Exception as e:
                error = str(e)
                if "Name or service not known" in error or "Failed to establish a new connection" in error:
                    raise Warning("Servidor fuera de servicio, favor de intentar mas tarde")
                else:
                    raise Warning(error)
                
            #_logger.info('something ... %s', response.text)
            json_response = response.json()
            xml_file_link = False
            estado_factura = json_response['estado_factura']
            if estado_factura == 'problemas_factura':
                raise UserError(_(json_response['problemas_message']))
            # Receive and stroe XML invoice
            if json_response.get('factura_xml'):
                xml_file_link = invoice.company_id.factura_dir + '/' + invoice.number.replace('/', '_') + '.xml'
                xml_file = open(xml_file_link, 'w')
                xml_invoice = base64.b64decode(json_response['factura_xml'])
                xml_file.write(xml_invoice.decode("utf-8"))
                xml_file.close()
                invoice._set_data_from_xml(xml_invoice)
            invoice.write({'estado_factura': estado_factura,
                           'xml_invoice_link': xml_file_link,
                           'factura_cfdi': True})
            invoice.message_post(body="CFDI emitido")
        return True
    
    
    @api.multi
    def action_cfdi_cancel(self):
        for invoice in self:
            if invoice.factura_cfdi:
                if invoice.estado_factura == 'factura_cancelada':
                    pass
                    # raise UserError(_('La factura ya fue cancelada, no puede volver a cancelarse.'))
                if not invoice.company_id.archivo_cer:
                    raise UserError(_('Falta la ruta del archivo .cer'))
                if not invoice.company_id.archivo_key:
                    raise UserError(_('Falta la ruta del archivo .key'))
                archivo_cer = self.company_id.archivo_cer
                archivo_key = self.company_id.archivo_key
                archivo_xml_link = invoice.company_id.factura_dir + '/' + invoice.move_name.replace('/', '_') + '.xml'
                with open(archivo_xml_link, 'rb') as cf:
                     archivo_xml = base64.b64encode(cf.read())
                values = {
                          'rfc': invoice.company_id.rfc,
                          'api_key': invoice.company_id.proveedor_timbrado,
                          'uuid': self.folio_fiscal,
                          'folio': self.folio,
                          'serie_factura': invoice.company_id.serie_factura,
                          'modo_prueba': invoice.company_id.modo_prueba,
                            'certificados': {
                                  'archivo_cer': archivo_cer.decode("utf-8"),
                                  'archivo_key': archivo_key.decode("utf-8"),
                                  'contrasena': invoice.company_id.contrasena,
                            },
                          'xml': archivo_xml.decode("utf-8"),
                          }
                if self.company_id.proveedor_timbrado == 'multifactura':
                    url = '%s' % ('http://facturacion.itadmin.com.mx/api/refund')
                elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                    url = '%s' % ('http://facturacion2.itadmin.com.mx/api/refund')
                elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                    url = '%s' % ('http://facturacion3.itadmin.com.mx/api/refund')
                elif self.company_id.proveedor_timbrado == 'gecoerp':
                    if self.company_id.modo_prueba:
                        #url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/refund/?handler=OdooHandler33')
                        url = '%s' % ('https://itadmin.gecoerp.com/refund/?handler=OdooHandler33')
                    else:
                        url = '%s' % ('https://itadmin.gecoerp.com/refund/?handler=OdooHandler33')
                try:
                    response = requests.post(url , 
                                         auth=None,verify=False, data=json.dumps(values), 
                                         headers={"Content-type": "application/json"})
                except Exception as e:
                    error = str(e)
                    if "Name or service not known" in error or "Failed to establish a new connection" in error:
                        raise Warning("Servidor fuera de servicio, favor de intentar mas tarde")
                    else:
                       raise Warning(error)
                _logger.info('something ... %s', response.text)
                json_response = response.json()

                log_msg = ''
                if json_response['estado_factura'] == 'problemas_factura':
                    raise UserError(_(json_response['problemas_message']))
                elif json_response['estado_factura'] == 'solicitud_cancelar':
                    #invoice.write({'estado_factura': json_response['estado_factura']})
                    log_msg = "Se solicitó cancelación de CFDI"
                    #raise Warning(_(json_response['problemas_message']))
                elif json_response.get('factura_xml', False):
                    if invoice.number:
                        xml_file_link = invoice.company_id.factura_dir + '/CANCEL_' + invoice.number.replace('/', '_') + '.xml'
                    else:
                        xml_file_link = invoice.company_id.factura_dir + '/CANCEL_' + invoice.move_name.replace('/', '_') + '.xml'
                    xml_file = open(xml_file_link, 'w')
                    xml_invoice = base64.b64decode(json_response['factura_xml'])
                    xml_file.write(xml_invoice.decode("utf-8"))
                    xml_file.close()
                    if invoice.number:
                        file_name = invoice.number.replace('/', '_') + '.xml'
                    else:
                        file_name = invoice.move_name.replace('/', '_') + '.xml'
                    self.env['ir.attachment'].sudo().create(
                                                {
                                                    'name': file_name,
                                                    'datas': json_response['factura_xml'],
                                                    'datas_fname': file_name,
                                                    'res_model': self._name,
                                                    'res_id': invoice.id,
                                                    'type': 'binary'
                                                })
                    log_msg = "CFDI Cancelado"
                invoice.write({'estado_factura': json_response['estado_factura']})
                invoice.message_post(body=log_msg)
 
 
    @api.multi
    def force_invoice_send(self):
        for inv in self:
            email_act = inv.action_invoice_sent()
            if email_act and email_act.get('context'):
                email_ctx = email_act['context']
                email_ctx.update(default_email_from=inv.company_id.email)
                inv.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        return True

    @api.model
    def check_cancel_status_by_cron(self):
        domain = [('type', '=', 'out_invoice'),('estado_factura', '=', 'solicitud_cancelar')]
        invoices = self.search(domain, order = 'id')
        for invoice in invoices:
            _logger.info('Solicitando estado de factura %s', invoice.folio_fiscal)
            archivo_xml_link = invoice.company_id.factura_dir + '/' + invoice.move_name.replace('/', '_') + '.xml'
            with open(archivo_xml_link, 'rb') as cf:
                 archivo_xml = base64.b64encode(cf.read())
            values = {
                 'rfc': invoice.company_id.rfc,
                 'api_key': invoice.company_id.proveedor_timbrado,
                 'modo_prueba': invoice.company_id.modo_prueba,
                 'uuid': invoice.folio_fiscal,
                 'xml': archivo_xml.decode("utf-8"),
                 }

            if invoice.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/consulta-cacelar')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % ('http://facturacion2.itadmin.com.mx/api/consulta-cacelar')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % ('http://facturacion3.itadmin.com.mx/api/consulta-cacelar')
            elif invoice.company_id.proveedor_timbrado == 'gecoerp':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/consulta-cacelar')

            try:
               response = requests.post(url, 
                                         auth=None,verify=False, data=json.dumps(values), 
                                         headers={"Content-type": "application/json"})
               #_logger.info('info enviada ...')
               json_response = response.json()
               #_logger.info('something ... %s', response.text)
            except Exception as e:
               _logger.info('log de la exception ... %s', response.text)
               json_response = {}
            if not json_response:
               return
            estado_factura = json_response['estado_consulta']
            if estado_factura == 'problemas_consulta':
                _logger.info('Error en la consulta %s', json_response['problemas_message'])
            elif estado_factura == 'consulta_correcta':
                if json_response['factura_xml'] == 'Cancelado':
                    _logger.info('Factura cancelada')
                    _logger.info('EsCancelable: %s', json_response['escancelable'])
                    _logger.info('EstatusCancelacion: %s', json_response['estatuscancelacion'])
                    invoice.action_cfdi_cancel()
                elif json_response['factura_xml'] == 'Vigente':
                    _logger.info('Factura vigente')
                    _logger.info('EsCancelable: %s', json_response['escancelable'])
                    _logger.info('EstatusCancelacion: %s', json_response['estatuscancelacion'])
                    if json_response['estatuscancelacion'] == 'Solicitud rechazada':
                        invoice.estado_factura = 'solicitud_rechazada'
            else:
                _logger.info('Error... %s', response.text)
        return True

    @api.multi
    def action_cfdi_rechazada(self):
        for invoice in self:
            if invoice.factura_cfdi:
                if invoice.estado_factura == 'solicitud_rechazada' or invoice.estado_factura == 'solicitud_cancelar':
                    invoice.estado_factura = 'factura_correcta'
                    # raise UserError(_('La factura ya fue cancelada, no puede volver a cancelarse.'))
 
 
    @api.model
    def action_generate_cfdi(self):
        for record in self:
            if record.state!='cancel' and record.estado_factura=='factura_no_generada':
                if record.state == 'draft':
                    record.action_invoice_open()
                    record.action_cfdi_generate()
                else:
                    record.action_cfdi_generate()

    @api.multi
    def action_invoice_cancel(self):
        for record in self:
           result = super(AccountInvoice, record).action_invoice_cancel()
           record.write({'number': record.move_name})
           return result
 
class MailTemplate(models.Model):
    "Templates for sending email"
    _inherit = 'mail.template'

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

        for template, template_res_ids in templates_to_res_ids.items():
            if template.report_template and template.report_template.report_name == 'account.report_invoice':
                for res_id in template_res_ids:
                    invoice = self.env[template.model].browse(res_id)
                    if not invoice.factura_cfdi:
                        continue
                    if invoice.estado_factura == 'factura_correcta' or invoice.estado_factura == 'solicitud_cancelar':
                        xml_name = invoice.company_id.factura_dir + '/' + invoice.number.replace('/', '_') + '.xml'
                        xml_file = open(xml_name, 'rb').read()
                        attachments = results[res_id]['attachments'] or []
                        attachments.append(('CDFI_' + invoice.number.replace('/', '_') + '.xml', 
                                            base64.b64encode(xml_file)))
                    else:
                        if invoice.number:
                            cancel_file_link = invoice.company_id.factura_dir + '/CANCEL_' + invoice.number.replace('/', '_') + '.xml'
                        else:
                            cancel_file_link = invoice.company_id.factura_dir + '/CANCEL_' + invoice.move_name.replace('/', '_') + '.xml'
                        with open(cancel_file_link, 'rb') as cf:
                            cancel_xml_file = cf.read()
                            attachments = []	
                            if invoice.number:
                                attachments.append(('CDFI_CANCEL_' + invoice.number.replace('/', '_') + '.xml', base64.b64encode(cancel_xml_file)))
                            else:
                                attachments.append(('CDFI_CANCEL_' + invoice.move_name.replace('/', '_') + '.xml', base64.b64encode(cancel_xml_file)))
                    results[res_id]['attachments'] = attachments
        return results

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    pedimento = fields.Char('Pedimento')
    predial = fields.Char('No. Predial')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:            
    
