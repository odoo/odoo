# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr
from odoo.tests.common import Form
from odoo.exceptions import UserError

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader
import base64
from odoo.addons.xades.models.xades import sign
import io

import logging

_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != 'l10n_ec_out_invoice':
            return res
        return journal.type == 'sale'

    def _post_invoice_edi(self, invoices, test_mode=False):
        if self.code != 'l10n_ec_out_invoice':
            return super()._post_invoice_edi(invoices, test_mode=test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._l10n_ec_document(invoice)
            res[invoice] = {'attachment': attachment}
        return res

    def _is_required_for_invoice(self, move):
        if self.code != 'l10n_ec_out_invoice':
            return super()._is_required_for_invoice(move)
        return True

    def _needs_web_services(self):
        self.ensure_one()
        if self.code != 'l10n_ec_out_invoice':
            return super()._needs_web_services()
        return True

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()
        return False if self.code == 'l10n_ec_out_invoice' else super()._is_embedding_to_invoice_pdf_needed()

    def _l10n_ec_document(self, invoice):
        #einvoice_tmpl = self.env['ir.ui.view'].search([('xml_id', '=', 'l10n_ec_edi.out_invoice')])
        data = {}
        data.update(self._l10n_ec_info_tributaria(invoice, invoice.name, '1'))
        data.update(self._l10n_ec_info_factura(invoice))
        
        detalles = self._l10n_ec_detalles(invoice)
        data.update(detalles)
        #data.update(self._compute_discount(detalles))
        einvoice = self.env['ir.ui.view'].render_public_asset('l10n_ec_edi.out_invoice',data)
        signed_doc = sign(einvoice, invoice.company_id.l10n_ec_edi_certificate, invoice.company_id.l10n_ec_edi_password,'#comprobante')
        return self.env['ir.attachment'].create({
            'name': invoice.name+'.xml',
            'datas': base64.encodestring(signed_doc),
            'mimetype': 'application/xml'
        })

    def _l10n_ec_info_tributaria(self, document, access_key, emission_code):
        """
        """
        company = document.company_id
        ##auth = self.get_auth(document)
        infoTributaria = {
            'ambiente': self.env.user.company_id.l10n_ec_edi_env,
            'tipoEmision': emission_code,
            'razonSocial': company.name,
            'nombreComercial': company.name,
            'ruc': company.partner_id.vat,
            'claveAcceso':  access_key,
            'codDoc': document.l10n_latam_document_type_id.code,
            'estab': '001',
            'ptoEmi': '001',
            'secuencial': '23458585',
            'dirMatriz': company.street
        }
        return infoTributaria

    def _l10n_ec_info_factura(self, invoice):
        """
        """
        def fix_date(fecha):
            d = '{0:%d/%m/%Y}'.format(fecha)
            return d

        def sum_tax_groups(groups):
            return sum([t[0] for t in invoice.amount_by_group if t[1] in groups])

        company = invoice.company_id
        partner = invoice.partner_id
        infoFactura = {
            'fechaEmision': fix_date(invoice.invoice_date),
            'dirEstablecimiento': company.street.replace('&','&amp;'),
            'obligadoContabilidad': 'SI',
            'tipoIdentificacionComprador': partner.l10n_latam_identification_type_id,  # noqa
            'razonSocialComprador': partner.name.replace('&','&amp;'),
            'identificacionComprador': partner.vat,
            'direccionComprador': ' '.join([partner.street or '', partner.street2 or '']).replace('\n','').replace('\r\n','').replace('&','&amp;'),
            'totalSinImpuestos': '%.2f' % (invoice.amount_untaxed),
            'totalDescuento': '0.00',
            'propina': '0.00',
            'importeTotal': '{:.2f}'.format(invoice.amount_total),
            'moneda': 'DOLAR',
            'formaPago': '01',
            'valorRetIva': '{:.2f}'.format(abs(sum_tax_groups(['ret_vat_srv', 'ret_vat_b']))),  # noqa
            'valorRetRenta': '{:.2f}'.format(abs(sum_tax_groups(['ret_ir']))),
            #'Resolucion':company.resolution_number,
            #'ret_agent': company.withholding_agent
        }
        
        totalConImpuestos = []
        for tax in invoice.line_ids.filtered(lambda t: t.tax_line_id):
            if tax.tax_group_id.l10n_ec_type in ['vat12', 'zero_vat']:
            
                totalImpuesto = {
                    'codigo': '2',
                    'codigoPorcentaje': '2',
                    'baseImponible': '{:.2f}'.format(tax.tax_base_amount),
                    'tarifa': tax.tax_line_id.amount,
                    'valor': '{:.2f}'.format(abs(tax.price_total))
                    }
                totalConImpuestos.append(totalImpuesto)
            if tax.tax_group_id.l10n_ec_type in ['irbp']:
                
                    totalImpuesto = {
                        'codigo': '5',
                        'codigoPorcentaje': '5001',
                        'baseImponible': '{:.2f}'.format(tax.tax_base_amount),
                        'tarifa': '0.02',
                        'valor': '{:.2f}'.format(abs(tax.price_total))
                        }
                    totalConImpuestos.append(totalImpuesto)
    
        infoFactura.update({'totalConImpuestos': totalConImpuestos})        
        return infoFactura

    def _l10n_ec_detalles(self, invoice):
        """
        """
        def fix_chars(code):
            special = [
                [u'%', ' '],
                [u'º', ' '],
                [u'Ñ', 'N'],
                [u'ñ', 'n'],
                [u'&', '&amp;']
            ]
            for f, r in special:
                code = code.replace(f, r)
            return code
        
        detalles = []
        for line in invoice.invoice_line_ids:
            codigoPrincipal = line.product_id and \
                line.product_id.default_code and \
                fix_chars(line.product_id.default_code) or '001'
            priced = line.price_unit * (1 - (line.discount or 0.00) / 100.0)
            discount = (line.price_unit - priced) * line.quantity
            detalle = {
                'codigoPrincipal': codigoPrincipal,
                'descripcion': fix_chars(line.name.strip().replace('\n', ''))[:254],
                'cantidad': '%.6f' % (line.quantity),
                'precioUnitario': '%.6f' % (line.price_unit),
                'descuento': '%.2f' % discount,
                'precioTotalSinImpuesto': '%.2f' % (line.price_subtotal)
            }
            impuestos = []
            for tax_line in line.tax_ids:
                if tax_line.tax_group_id.l10n_ec_type in ['vat12', 'zero_vat']:
                    impuesto = {
                        'type': 'vat12',
                        'codigo': '2',
                        'codigoPorcentaje': '2',  # noqa
                        'tarifa': tax_line.amount,
                        'baseImponible': '{:.2f}'.format(line.price_subtotal),
                        'valor': '{:.2f}'.format(line.price_subtotal *
                                                 tax_line.amount/100.0)
                    }
                    impuestos.append(impuesto)
                    
                if tax_line.tax_group_id.l10n_ec_type in ['irbp']:
                
                    impuesto = {
                        'type': 'irbp',
                        'codigo': '5',
                        'codigoPorcentaje': '5001',
                        'baseImponible': '{:.2f}'.format(line.price_subtotal),
                        'tarifa': '0.02',
                        'valor': '{:.2f}'.format(tax_line._compute_amount(line.price_subtotal, line.price_unit, line.quantity, line.product_id))
                        }
                    impuestos.append(impuesto)


            ice = [imp for imp in impuestos if imp['type']=='ice']
            vat = [imp for imp in impuestos if imp['type']=='vat12']
            if len(ice)>0:
                ice = ice[0]
                if len(vat)>0:
                    vat=vat[0]
                    vatbase = float(vat['baseImponible']) + float(ice['valor'])
                    tarifa = float(vat['tarifa'])
                    vat.update({
                        'baseImponible': '{:.2f}'.format(vatbase),
                        'valor': '{:.2f}'.format(vatbase * tarifa/100.0)
                    })    
                    impuestos = [vat,ice]
            detalle.update({'impuestos': impuestos})
            detalles.append(detalle)
            #detalles = self._merge_promos(detalles)
        return {'detalles': detalles}
