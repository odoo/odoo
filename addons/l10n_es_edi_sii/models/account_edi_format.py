# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from urllib3.util.ssl_ import create_urllib3_context, DEFAULT_CIPHERS
from OpenSSL.crypto import load_certificate, load_privatekey, FILETYPE_PEM
from zeep.transports import Transport

from odoo import fields
from odoo.tools import html_escape

import math
import json
import requests
import zeep

from odoo import models, _


# Custom patches to perform the WSDL requests.

EUSKADI_CIPHERS = f"{DEFAULT_CIPHERS}:!DH"


class PatchedHTTPAdapter(requests.adapters.HTTPAdapter):
    """ An adapter to block DH ciphers which may not work for the tax agencies called"""

    def init_poolmanager(self, *args, **kwargs):
        # OVERRIDE
        kwargs['ssl_context'] = create_urllib3_context(ciphers=EUSKADI_CIPHERS)
        return super().init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        # OVERRIDE
        # The last parameter is only used by the super method to check if the file exists.
        # In our case, cert is an odoo record 'l10n_es_edi.certificate' so not a path to a file.
        # By putting 'None' as last parameter, we ensure the check about TLS configuration is
        # still made without checking temporary files exist.
        super().cert_verify(conn, url, verify, None)
        conn.cert_file = cert
        conn.key_file = cert

    def get_connection(self, url, proxies=None):
        # OVERRIDE
        # Patch the OpenSSLContext to decode the certificate in-memory.
        conn = super().get_connection(url, proxies=proxies)

        context = conn.conn_kw['ssl_context']

        def patched_load_cert_chain(l10n_es_odoo_certificate, keyfile=None, password=None):
            cert_file, key_file, dummy = l10n_es_odoo_certificate._decode_certificate()
            cert_obj = load_certificate(FILETYPE_PEM, cert_file)
            pkey_obj = load_privatekey(FILETYPE_PEM, key_file)

            context._ctx.use_certificate(cert_obj)
            context._ctx.use_privatekey(pkey_obj)

        context.load_cert_chain = patched_load_cert_chain

        return conn


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # ES EDI
    # -------------------------------------------------------------------------

    def _l10n_es_edi_get_invoices_tax_details_info(self, invoice, filter_invl_to_apply=None):

        def grouping_key_generator(tax_values):
            tax = tax_values['tax_id']
            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
            }

        def filter_to_apply(tax_values):
            # For intra-community, we do not take into account the negative repartition line
            return tax_values['tax_repartition_line_id'].factor_percent > 0.0

        def full_filter_invl_to_apply(invoice_line):
            if 'ignore' in invoice_line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type'):
                return False
            return filter_invl_to_apply(invoice_line) if filter_invl_to_apply else True

        tax_details = invoice._prepare_edi_tax_details(
            grouping_key_generator=grouping_key_generator,
            filter_invl_to_apply=full_filter_invl_to_apply,
            filter_to_apply=filter_to_apply,
        )
        sign = -1 if invoice.is_sale_document() else 1

        tax_details_info = defaultdict(dict)

        # Detect for which is the main tax for 'recargo'. Since only a single combination tax + recargo is allowed
        # on the same invoice, this can be deduced globally.

        recargo_tax_details = {} # Mapping between main tax and recargo tax details
        invoice_lines = invoice.invoice_line_ids.filtered(lambda x: not x.display_type)
        if filter_invl_to_apply:
            invoice_lines = invoice_lines.filtered(filter_invl_to_apply)
        for line in invoice_lines:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            recargo_tax = [t for t in taxes if t.l10n_es_type == 'recargo']
            if recargo_tax and taxes:
                recargo_main_tax = taxes.filtered(lambda x: x.l10n_es_type in ('sujeto', 'sujeto_isp'))[:1]
                if not recargo_tax_details.get(recargo_main_tax):
                    recargo_tax_details[recargo_main_tax] = [
                        x for x in tax_details['tax_details'].values()
                        if x['group_tax_details'][0]['tax_id'] == recargo_tax[0]
                    ][0]

        tax_amount_deductible = 0.0
        tax_amount_retention = 0.0
        base_amount_not_subject = 0.0
        base_amount_not_subject_loc = 0.0
        tax_subject_info_list = []
        tax_subject_isp_info_list = []
        for tax_values in tax_details['tax_details'].values():

            if invoice.is_sale_document():
                # Customer invoices

                if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp'):
                    tax_amount_deductible += tax_values['tax_amount']

                    base_amount = sign * tax_values['base_amount']
                    tax_info = {
                        'TipoImpositivo': tax_values['applied_tax_amount'],
                        'BaseImponible': round(base_amount, 2),
                        'CuotaRepercutida': round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                    }

                    recargo = recargo_tax_details.get(tax_values['group_tax_details'][0]['tax_id'])
                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']

                    if tax_values['l10n_es_type'] == 'sujeto':
                        tax_subject_info_list.append(tax_info)
                    else:
                        tax_subject_isp_info_list.append(tax_info)

                elif tax_values['l10n_es_type'] == 'exento':
                    tax_details_info['Sujeta'].setdefault('Exenta', {'DetalleExenta': []})
                    tax_details_info['Sujeta']['Exenta']['DetalleExenta'].append({
                        'BaseImponible': round(sign * tax_values['base_amount'], 2),
                        'CausaExencion': tax_values['l10n_es_exempt_reason'],
                    })
                elif tax_values['l10n_es_type'] == 'retencion':
                    tax_amount_retention += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto':
                    base_amount_not_subject += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto_loc':
                    base_amount_not_subject_loc += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'ignore':
                    continue

                if tax_subject_isp_info_list and not tax_subject_info_list:
                    tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S2'}
                elif not tax_subject_isp_info_list and tax_subject_info_list:
                    tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S1'}
                elif tax_subject_isp_info_list and tax_subject_info_list:
                    tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S3'}

                if tax_subject_info_list:
                    tax_details_info['Sujeta']['NoExenta'].setdefault('DesgloseIVA', {})
                    tax_details_info['Sujeta']['NoExenta']['DesgloseIVA'].setdefault('DetalleIVA', [])
                    tax_details_info['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] += tax_subject_info_list
                if tax_subject_isp_info_list:
                    tax_details_info['Sujeta']['NoExenta'].setdefault('DesgloseIVA', {})
                    tax_details_info['Sujeta']['NoExenta']['DesgloseIVA'].setdefault('DetalleIVA', [])
                    tax_details_info['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] += tax_subject_isp_info_list

            else:
                # Vendor bills
                if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc'):
                    tax_amount_deductible += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'retencion':
                    tax_amount_retention += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto':
                    base_amount_not_subject += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto_loc':
                    base_amount_not_subject_loc += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'ignore':
                    continue

                if tax_values['l10n_es_type'] not in ['retencion', 'recargo']: # = in sujeto/sujeto_isp/no_deducible
                    base_amount = sign * tax_values['base_amount']
                    tax_details_info.setdefault('DetalleIVA', [])
                    tax_info = {
                        'BaseImponible': round(base_amount, 2),
                    }
                    if tax_values['applied_tax_amount'] > 0.0:
                        tax_info.update({
                            'TipoImpositivo': tax_values['applied_tax_amount'],
                            'CuotaSoportada': round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                        })
                    if tax_values['l10n_es_bien_inversion']:
                        tax_info['BienInversion'] = 'S'
                    recargo = recargo_tax_details.get(tax_values['group_tax_details'][0]['tax_id'])
                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']
                    tax_details_info['DetalleIVA'].append(tax_info)

        if not invoice.company_id.currency_id.is_zero(base_amount_not_subject) and invoice.is_sale_document():
            tax_details_info['NoSujeta']['ImportePorArticulos7_14_Otros'] = round(sign * base_amount_not_subject, 2)
        if not invoice.company_id.currency_id.is_zero(base_amount_not_subject_loc) and invoice.is_sale_document():
            tax_details_info['NoSujeta']['ImporteTAIReglasLocalizacion'] = round(sign * base_amount_not_subject_loc, 2)

        return {
            'tax_details_info': tax_details_info,
            'tax_details': tax_details,
            'tax_amount_deductible': tax_amount_deductible,
            'tax_amount_retention': tax_amount_retention,
            'base_amount_not_subject': base_amount_not_subject,
        }

    def _l10n_es_edi_get_partner_info(self, partner):
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        partner_info = {}
        IDOtro_ID = partner.vat or 'NO_DISPONIBLE'

        if (not partner.country_id or partner.country_id.code == 'ES') and partner.vat:
            # ES partner with VAT.
            partner_info['NIF'] = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat
        elif partner.country_id.code in eu_country_codes:
            # European partner.
            partner_info['IDOtro'] = {'IDType': '02', 'ID': IDOtro_ID}
        else:
            partner_info['IDOtro'] = {'ID': IDOtro_ID}
            if partner.vat:
                partner_info['IDOtro']['IDType'] = '04'
            else:
                partner_info['IDOtro']['IDType'] = '06'
            if partner.country_id:
                partner_info['IDOtro']['CodigoPais'] = partner.country_id.code
        return partner_info

    def _l10n_es_edi_get_invoices_info(self, invoices):
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        simplified_partner = self.env.ref("l10n_es_edi_sii.partner_simplified")

        info_list = []
        for invoice in invoices:
            com_partner = invoice.commercial_partner_id
            is_simplified = invoice.partner_id == simplified_partner

            info = {
                'PeriodoLiquidacion': {
                    'Ejercicio': str(invoice.date.year),
                    'Periodo': str(invoice.date.month).zfill(2),
                },
                'IDFactura': {
                    'FechaExpedicionFacturaEmisor': invoice.invoice_date.strftime('%d-%m-%Y'),
                },
            }

            if invoice.is_sale_document():
                invoice_node = info['FacturaExpedida'] = {}
            else:
                invoice_node = info['FacturaRecibida'] = {}

            # === Partner ===

            partner_info = self._l10n_es_edi_get_partner_info(com_partner)

            # === Invoice ===

            invoice_node['DescripcionOperacion'] = invoice.invoice_origin or 'manual'
            if invoice.is_sale_document():
                info['IDFactura']['IDEmisorFactura'] = {'NIF': invoice.company_id.vat[2:]}
                info['IDFactura']['NumSerieFacturaEmisor'] = invoice.name[:60]
                if not is_simplified:
                    invoice_node['Contraparte'] = {
                        **partner_info,
                        'NombreRazon': com_partner.name[:120],
                    }

                if not com_partner.country_id or com_partner.country_id.code in eu_country_codes:
                    invoice_node['ClaveRegimenEspecialOTrascendencia'] = '01'
                else:
                    invoice_node['ClaveRegimenEspecialOTrascendencia'] = '02'
            else:
                info['IDFactura']['IDEmisorFactura'] = partner_info
                info['IDFactura']['NumSerieFacturaEmisor'] = invoice.ref[:60]
                if not is_simplified:
                    invoice_node['Contraparte'] = {
                        **partner_info,
                        'NombreRazon': com_partner.name[:120],
                    }

                if invoice.l10n_es_registration_date:
                    invoice_node['FechaRegContable'] = invoice.l10n_es_registration_date.strftime('%d-%m-%Y')
                else:
                    invoice_node['FechaRegContable'] = fields.Date.context_today(self).strftime('%d-%m-%Y')

                if not com_partner.country_id or com_partner.country_id.code == 'ES':
                    invoice_node['ClaveRegimenEspecialOTrascendencia'] = '01'
                else:
                    invoice_node['ClaveRegimenEspecialOTrascendencia'] = '09'

            if invoice.move_type == 'out_invoice':
                invoice_node['TipoFactura'] = 'F2' if is_simplified else 'F1'
            elif invoice.move_type == 'out_refund':
                invoice_node['TipoFactura'] = 'R5' if is_simplified else 'R1'
                invoice_node['TipoRectificativa'] = 'I'
            elif invoice.move_type == 'in_invoice':
                invoice_node['TipoFactura'] = 'F1'
            elif invoice.move_type == 'in_refund':
                invoice_node['TipoFactura'] = 'R4'
                invoice_node['TipoRectificativa'] = 'I'

            # === Taxes ===

            sign = -1 if invoice.is_sale_document() else 1

            if invoice.is_sale_document():
                # Customer invoices

                if com_partner.country_id.code in ('ES', False) and not (com_partner.vat or '').startswith("ESN"):
                    tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info(invoice)
                    invoice_node['TipoDesglose'] = {'DesgloseFactura': tax_details_info_vals['tax_details_info']}

                    invoice_node['ImporteTotal'] = round(sign * (
                        tax_details_info_vals['tax_details']['base_amount']
                        + tax_details_info_vals['tax_details']['tax_amount']
                        - tax_details_info_vals['tax_amount_retention']
                    ), 2)
                else:
                    tax_details_info_service_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                        invoice,
                        filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
                    )
                    tax_details_info_consu_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                        invoice,
                        filter_invl_to_apply=lambda x: any(t.tax_scope == 'consu' for t in x.tax_ids)
                    )

                    if tax_details_info_service_vals['tax_details_info']:
                        invoice_node.setdefault('TipoDesglose', {})
                        invoice_node['TipoDesglose'].setdefault('DesgloseTipoOperacion', {})
                        invoice_node['TipoDesglose']['DesgloseTipoOperacion']['PrestacionServicios'] = tax_details_info_service_vals['tax_details_info']
                    if tax_details_info_consu_vals['tax_details_info']:
                        invoice_node.setdefault('TipoDesglose', {})
                        invoice_node['TipoDesglose'].setdefault('DesgloseTipoOperacion', {})
                        invoice_node['TipoDesglose']['DesgloseTipoOperacion']['Entrega'] = tax_details_info_consu_vals['tax_details_info']

                    invoice_node['ImporteTotal'] = round(sign * (
                        tax_details_info_service_vals['tax_details']['base_amount']
                        + tax_details_info_service_vals['tax_details']['tax_amount']
                        - tax_details_info_service_vals['tax_amount_retention']
                        + tax_details_info_consu_vals['tax_details']['base_amount']
                        + tax_details_info_consu_vals['tax_details']['tax_amount']
                        - tax_details_info_consu_vals['tax_amount_retention']
                    ), 2)

            else:
                # Vendor bills

                tax_details_info_isp_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    invoice,
                    filter_invl_to_apply=lambda x: any(t for t in x.tax_ids if t.l10n_es_type == 'sujeto_isp'),
                )
                tax_details_info_other_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    invoice,
                    filter_invl_to_apply=lambda x: not any(t for t in x.tax_ids if t.l10n_es_type == 'sujeto_isp'),
                )

                invoice_node['DesgloseFactura'] = {}
                if tax_details_info_isp_vals['tax_details_info']:
                    invoice_node['DesgloseFactura']['InversionSujetoPasivo'] = tax_details_info_isp_vals['tax_details_info']
                if tax_details_info_other_vals['tax_details_info']:
                    invoice_node['DesgloseFactura']['DesgloseIVA'] = tax_details_info_other_vals['tax_details_info']

                invoice_node['ImporteTotal'] = round(sign * (
                    tax_details_info_isp_vals['tax_details']['base_amount']
                    + tax_details_info_isp_vals['tax_details']['tax_amount']
                    - tax_details_info_isp_vals['tax_amount_retention']
                    + tax_details_info_other_vals['tax_details']['base_amount']
                    + tax_details_info_other_vals['tax_details']['tax_amount']
                    - tax_details_info_other_vals['tax_amount_retention']
                ), 2)

                invoice_node['CuotaDeducible'] = round(sign * (
                    tax_details_info_isp_vals['tax_amount_deductible']
                    + tax_details_info_other_vals['tax_amount_deductible']
                ), 2)

            info_list.append(info)
        return info_list

    def _l10n_es_edi_web_service_aeat_vals(self, invoices):
        if invoices[0].is_sale_document():
            return {'url': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii_1_1/fact/ws/SuministroFactEmitidas.wsdl'}
        else:
            return {'url': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii_1_1/fact/ws/SuministroFactRecibidas.wsdl'}

    def _l10n_es_edi_web_service_bizkaia_vals(self, invoices):
        if invoices[0].is_sale_document():
            return {
                'url': 'https://www.bizkaia.eus/ogasuna/sii/documentos/SuministroFactEmitidas.wsdl',
                'test_url': 'https://pruapps.bizkaia.eus/SSII-FACT/ws/fe/SiiFactFEV1SOAP',
            }
        else:
            return {
                'url': 'https://www.bizkaia.eus/ogasuna/sii/documentos/SuministroFactRecibidas.wsdl',
                'test_url': 'https://pruapps.bizkaia.eus/SSII-FACT/ws/fr/SiiFactFRV1SOAP',
            }

    def _l10n_es_edi_web_service_gipuzkoa_vals(self, invoices):
        if invoices[0].is_sale_document():
            return {
                'url': 'https://egoitza.gipuzkoa.eus/ogasuna/sii/ficheros/v1.1/SuministroFactEmitidas.wsdl',
                'test_url': 'https://sii-prep.egoitza.gipuzkoa.eus/JBS/HACI/SSII-FACT/ws/fe/SiiFactFEV1SOAP',
            }
        else:
            return {
                'url': 'https://egoitza.gipuzkoa.eus/ogasuna/sii/ficheros/v1.1/SuministroFactRecibidas.wsdl',
                'test_url': 'https://sii-prep.egoitza.gipuzkoa.eus/JBS/HACI/SSII-FACT/ws/fr/SiiFactFRV1SOAP',
            }

    def _l10n_es_edi_call_web_service_sign(self, invoices, info_list):
        company = invoices.company_id

        # All are sharing the same value, see '_get_batch_key'.
        csv_number = invoices.mapped('l10n_es_edi_csv')[0]

        # Set registration date
        invoices.filtered(lambda inv: not inv.l10n_es_registration_date).write({
            'l10n_es_registration_date': fields.Date.context_today(self),
        })

        # === Call the web service ===

        # Get connection data.
        l10n_es_edi_tax_agency = company.mapped('l10n_es_edi_tax_agency')[0]
        connection_vals = getattr(self, f'_l10n_es_edi_web_service_{l10n_es_edi_tax_agency}_vals')(invoices)

        header = {
            'IDVersionSii': '1.1',
            'Titular': {
                'NombreRazon': company.name[:120],
                'NIF': company.vat[2:],
            },
            'TipoComunicacion': 'A1' if csv_number else 'A0',
        }

        session = requests.Session()
        session.cert = company.l10n_es_edi_certificate_id
        session.mount('https://', PatchedHTTPAdapter())

        transport = Transport(operation_timeout=60, timeout=60, session=session)
        client = zeep.Client(connection_vals['url'], transport=transport)

        if invoices[0].is_sale_document():
            service_name = 'SuministroFactEmitidas'
        else:
            service_name = 'SuministroFactRecibidas'
        if company.l10n_es_edi_test_env and not connection_vals.get('test_url'):
            service_name += 'Pruebas'

        # Establish the connection.
        serv = client.bind('siiService', service_name)
        if company.l10n_es_edi_test_env and connection_vals.get('test_url'):
            serv._binding_options['address'] = connection_vals['test_url']

        msg = ''
        try:
            if invoices[0].is_sale_document():
                res = serv.SuministroLRFacturasEmitidas(header, info_list)
            else:
                res = serv.SuministroLRFacturasRecibidas(header, info_list)
        except requests.exceptions.SSLError as error:
            msg = _("The SSL certificate could not be validated.")
        except zeep.exceptions.Error as error:
            msg = _("Networking error:\n%s") % error
        except Exception as error:
            msg = str(error)
        finally:
            if msg:
                return {inv: {
                    'error': msg,
                    'blocking_level': 'warning',
                } for inv in invoices}

        # Process response.

        if not res or not res.RespuestaLinea:
            return {inv: {
                'error': _("The web service is not responding"),
                'blocking_level': 'warning',
            } for inv in invoices}

        resp_state = res["EstadoEnvio"]
        l10n_es_edi_csv = res['CSV']

        if resp_state == 'Correcto':
            invoices.write({'l10n_es_edi_csv': l10n_es_edi_csv})
            return {inv: {'success': True} for inv in invoices}

        results = {}
        for respl in res.RespuestaLinea:
            invoice_number = respl.IDFactura.NumSerieFacturaEmisor

            # Retrieve the corresponding invoice.
            # Note: ref can be the same for different partners but there is no enough information on the response
            # to match the partner.

            # Note: Invoices are batched per move_type.
            if invoices[0].is_sale_document():
                inv = invoices.filtered(lambda x: x.name[:60] == invoice_number)
            else:
                # 'ref' can be the same for different partners.
                candidates = invoices.filtered(lambda x: x.ref[:60] == invoice_number)
                if len(candidates) >= 1:
                    respl_partner_info = respl.IDFactura.IDEmisorFactura
                    inv = None
                    for candidate in candidates:
                        partner_info = self._l10n_es_edi_get_partner_info(candidate.commercial_partner_id)
                        if partner_info.get('NIF') and partner_info['NIF'] == respl_partner_info.NIF:
                            inv = candidate
                            break
                        if partner_info.get('IDOtro') and all(getattr(respl_partner_info.IDOtro, k) == v
                                                           for k, v in partner_info['IDOtro'].items()):
                            inv = candidate
                            break

                    if not inv:
                        # This case shouldn't happen and means there is something wrong in this code. However, we can't
                        # raise anything since the document has already been approved by the government. The result
                        # will only be a badly logged message into the chatter so, not a big deal.
                        inv = candidates[0]
                else:
                    inv = candidates

            resp_line_state = respl.EstadoRegistro
            if resp_line_state in ('Correcto', 'AceptadoConErrores'):
                inv.l10n_es_edi_csv = l10n_es_edi_csv
                results[inv] = {'success': True}
                if resp_line_state == 'AceptadoConErrores':
                    inv.message_post(body=_("This was accepted with errors: ") + html_escape(respl.DescripcionErrorRegistro))
            elif respl.RegistroDuplicado:
                results[inv] = {'success': True}
                inv.message_post(body=_("We saw that this invoice was sent correctly before, but we did not treat "
                                        "the response.  Make sure it is not because of a wrong configuration."))
            else:
                results[inv] = {
                    'error': _("[%s] %s", respl.CodigoErrorRegistro, respl.DescripcionErrorRegistro),
                    'blocking_level': 'error',
                }

        return results

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        if self.code != 'es_sii':
            return super()._is_required_for_invoice(invoice)

        return invoice.l10n_es_edi_is_required

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == 'es_sii' or super()._needs_web_services()

    def _support_batching(self, move=None, state=None, company=None):
        # OVERRIDE
        if self.code != 'es_sii':
            return super()._support_batching(move=move, state=state, company=company)

        return state == 'to_send' and move.is_invoice()

    def _get_batch_key(self, move, state):
        # OVERRIDE
        if self.code != 'es_sii':
            return super()._get_batch_key(move, state)

        return move.move_type, move.l10n_es_edi_csv

    def _check_move_configuration(self, move):
        # OVERRIDE
        res = super()._check_move_configuration(move)
        if self.code != 'es_sii':
            return res

        if not move.company_id.vat:
            res.append(_("VAT number is missing on company %s", move.company_id.display_name))
        if not move.partner_id.vat:
            res.append(_("VAT number needs to be configured on the partner %s", move.partner_id.display_name))
        for line in move.invoice_line_ids.filtered(lambda line: not line.display_type):
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            recargo_count = taxes.mapped('l10n_es_type').count('recargo')
            retention_count = taxes.mapped('l10n_es_type').count('retencion')
            sujeto_count = taxes.mapped('l10n_es_type').count('sujeto')
            no_sujeto_count = taxes.mapped('l10n_es_type').count('no_sujeto')
            no_sujeto_loc_count = taxes.mapped('l10n_es_type').count('no_sujeto_loc')
            if retention_count > 1:
                res.append(_("Line %s should only have one retention tax.", line.display_name))
            if recargo_count > 1:
                res.append(_("Line %s should only have one recargo tax.", line.display_name))
            if sujeto_count > 1:
                res.append(_("Line %s should only have one sujeto tax.", line.display_name))
            if no_sujeto_count > 1:
                res.append(_("Line %s should only have one no sujeto tax.", line.display_name))
            if no_sujeto_loc_count > 1:
                res.append(_("Line %s should only have one no sujeto (localizations) tax.", line.display_name))
            if sujeto_count + no_sujeto_loc_count + no_sujeto_count > 1:
                res.append(_("Line %s should only have one main tax.", line.display_name))
        if move.move_type in ('in_invoice', 'in_refund'):
            if not move.ref:
                res.append(_("You should put a vendor reference on this vendor bill. "))
        return res

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        if self.code != 'es_sii':
            return super()._is_compatible_with_journal(journal)

        return journal.country_code == 'ES'

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        if self.code != 'es_sii':
            return super()._post_invoice_edi(invoices, test_mode=test_mode)

        # Ensure a certificate is available.
        certificate = invoices.company_id.l10n_es_edi_certificate_id
        if not certificate:
            return {inv: {
                'error': _("Please configure the certificate for SII."),
                'blocking_level': 'error',
            } for inv in invoices}

        # Ensure a tax agency is available.
        l10n_es_edi_tax_agency = invoices.company_id.mapped('l10n_es_edi_tax_agency')[0]
        if not l10n_es_edi_tax_agency:
            return {inv: {
                'error': _("Please specify a tax agency on your company for SII."),
                'blocking_level': 'error',
            } for inv in invoices}

        # Generate the JSON.
        info_list = self._l10n_es_edi_get_invoices_info(invoices)

        # Call the web service.
        if test_mode:
            res = {inv: {'success': True} for inv in invoices}
        else:
            res = self._l10n_es_edi_call_web_service_sign(invoices, info_list)

        for inv in invoices:
            if res.get(inv, {}).get('success'):
                attachment = self.env['ir.attachment'].create({
                    'type': 'binary',
                    'name': 'jsondump.json',
                    'raw': json.dumps(info_list),
                    'mimetype': 'application/json',
                    'res_model': inv._name,
                    'res_id': inv.id,
                })
                res[inv] = {'attachment': attachment}
        return res
