# -*- coding: utf-8 -*-
from odoo import models,fields,api
from odoo.exceptions import Warning
import os
from lxml import etree
import base64
import json
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.units import mm

class import_account_payment_from_xml(models.TransientModel):
    _name ='import.account.payment.from.xml'

    import_file = fields.Binary("Importar Archivo",required=False)
    file_name = fields.Char("Nombre del archivo")
    payment_id = fields.Many2one("account.payment",'Payment')
    
    
    @api.multi
    def import_xml_file_button(self):
        self.ensure_one()
        if not self.import_file:
            raise Warning("Seleccione primero el archivo.")
        p, ext = os.path.splitext(self.file_name)
        if ext[1:].lower() !='xml':
            raise Warning(_("Formato no soportado \"{}\", importa solo archivos XML").format(self.file_name))
        
        file_content = base64.b64decode(self.import_file)
        tree = etree.fromstring(file_content)
        payment_vals = {
            'cep_sello': tree.get('sello'),
            'cep_numeroCertificado' : tree.get('numeroCertificado',tree.get('NumeroCertificado')),
            'cep_cadenaCDA' : tree.get('cadenaCDA',tree.get('CadenaCDA')),
            'cep_claveSPEI' : tree.get('ClaveSPEI',tree.get('claveSPEI')),
            }
        self.payment_id.write(payment_vals)
        return True
    
    @api.multi
    def import_xml_file_button_cargar(self):
        self.ensure_one()
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id'))
        if not self.import_file:
            raise Warning("Seleccione primero el archivo.")
        p, ext = os.path.splitext(self.file_name)
        if ext[1:].lower() !='xml':
            raise Warning(_("Formato no soportado \"{}\", importa solo archivos XML").format(self.file_name))
        
        NSMAP = {
                 'xsi':'http://www.w3.org/2001/XMLSchema-instance',
                 'cfdi':'http://www.sat.gob.mx/cfd/3', 
                 'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                 }

        file_content = base64.b64decode(self.import_file)
        xml_data = etree.fromstring(file_content)
        Emisor = xml_data.find('cfdi:Emisor', NSMAP)
        Receptor = xml_data.find('cfdi:Receptor', NSMAP)
        RegimenFiscal = Emisor.find('cfdi:RegimenFiscal', NSMAP)
        Complemento = xml_data.find('cfdi:Complemento', NSMAP)
        TimbreFiscalDigital = Complemento.find('tfd:TimbreFiscalDigital', NSMAP)
        
        xml_file_link = invoice_id.company_id.factura_dir + '/' + invoice_id.number.replace('/', '_') + '.xml'

        amount_str = str(xml_data.attrib['Total']).split('.')
        qr_value = 'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?&id=%s&re=%s&rr=%s&tt=%s.%s&fe=%s' % (TimbreFiscalDigital.attrib['UUID'],
                                                 invoice_id.company_id.rfc, 
                                                 invoice_id.partner_id.rfc,
                                                 amount_str[0].zfill(10),
                                                 len(amount_str) == 2 and amount_str[1].ljust(6, '0') or '000000',
                                                 str(TimbreFiscalDigital.attrib['SelloCFD'])[-8:],
                                                 )
        options = {'width': 275 * mm, 'height': 275 * mm}
        ret_val = createBarcodeDrawing('QR', value=qr_value, **options)
        qrcode_image = base64.encodestring(ret_val.asString('jpg'))

        cargar_values = {
            'methodo_pago': xml_data.attrib['MetodoPago'],
            'forma_pago' : xml_data.attrib['FormaPago'], 
            'uso_cfdi': Receptor.attrib['UsoCFDI'],
            'folio_fiscal' : TimbreFiscalDigital.attrib['UUID'],
            'tipo_comprobante': xml_data.attrib['TipoDeComprobante'],
            'fecha_factura': TimbreFiscalDigital.attrib['FechaTimbrado'] and parse(TimbreFiscalDigital.attrib['FechaTimbrado']).strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False,
            'xml_invoice_link': xml_file_link,
            'factura_cfdi': True,
            'estado_factura': 'factura_correcta',
            'numero_cetificado' : xml_data.attrib['NoCertificado'],
            'cetificaso_sat' : TimbreFiscalDigital.attrib['NoCertificadoSAT'],
            'fecha_certificacion' : TimbreFiscalDigital.attrib['FechaTimbrado'],
            'selo_digital_cdfi' : TimbreFiscalDigital.attrib['SelloCFD'],
            'selo_sat' : TimbreFiscalDigital.attrib['SelloSAT'],
            'tipocambio' : xml_data.find('TipoCambio') and xml_data.attrib['TipoCambio'] or '1',
            'moneda': xml_data.attrib['Moneda'],
            'number_folio': xml_data.find('Folio') and xml_data.attrib['Folio'] or ' ',
            'cadena_origenal' : '||%s|%s|%s|%s|%s||' % (TimbreFiscalDigital.attrib['Version'], TimbreFiscalDigital.attrib['UUID'], TimbreFiscalDigital.attrib['FechaTimbrado'],
                                                         TimbreFiscalDigital.attrib['SelloCFD'], TimbreFiscalDigital.attrib['NoCertificadoSAT']),
            'qrcode_image': qrcode_image
            }
        invoice_id.write(cargar_values)

        xml_file = open(xml_file_link, 'w')
        xml_invoice = base64.b64decode(self.import_file)
        xml_file.write(xml_invoice.decode("utf-8"))
        xml_file.close()

        return True


