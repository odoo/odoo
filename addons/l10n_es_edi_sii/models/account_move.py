# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import json
import math
import requests

from odoo import api, fields, models
from odoo.tools import html_escape, zeep
from odoo.tools.float_utils import float_round
from odoo.addons.certificate.tools import CertificateAdapter
from markupsafe import Markup

EUSKADI_CIPHERS = "DEFAULT:!DH"

AEAT_BASE_URL = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/"
    "dep/aplicaciones/es/aeat/ssii_1_1/fact/ws"
)
AEAT_TEST_BASE_URL = "https://prewww1.aeat.es/wlpl/SSII-FACT/ws"

BIZKAIA_BASE_URL = "https://www.bizkaia.eus/ogasuna/sii/documentos"
BIZKAIA_TEST_BASE_URL = "https://pruapps.bizkaia.eus/SSII-FACT/ws"

GIPUZKOA_BASE_URL = "https://egoitza.gipuzkoa.eus/ogasuna/sii/ficheros/v1.1"
GIPUZKOA_TEST_BASE_URL = "https://sii-prep.egoitza.gipuzkoa.eus/JBS/HACI/SSII-FACT/ws"


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_is_required = fields.Boolean(
        string="Is the Spanish EDI needed",
        compute='_compute_l10n_es_edi_is_required'
    )
    l10n_es_edi_csv = fields.Char(string="CSV return code", copy=False, tracking=True)
    # Technical field to keep the date the invoice was sent the first time as
    # the date the invoice was registered into the system.
    l10n_es_registration_date = fields.Date(
        string="Registration Date", copy=False,
    )
    l10n_es_edi_sii_state = fields.Selection(
        [
            ('to_send', "To Send"),
            ('sent', "Sent"),
            ('cancel', "Cancelled")
        ],
        string="Spain SII Status",
        copy=False,
        tracking=True,
    )
    l10n_es_edi_sii_error = fields.Html(readonly=True, copy=False)
    l10n_es_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="SII JSON",
        compute=lambda self: self._compute_linked_attachment_id(
            'l10n_es_edi_attachment_id',
            'l10n_es_edi_sii_json_file',
        ),
        depends=['l10n_es_edi_sii_json_file']
    )
    l10n_es_edi_sii_json_file = fields.Binary(
        string="SII JSON Payload File",
        attachment=True,
        copy=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id', 'invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_is_required(self):
        for move in self:
            has_tax = True
            # Check it is not an importation invoice (which will be report through the DUA invoice)
            if move.is_purchase_document():
                taxes = move.invoice_line_ids.tax_ids
                has_tax = any(t.l10n_es_type and t.l10n_es_type != 'ignore' for t in taxes)
            move.l10n_es_edi_is_required = move.is_invoice() \
                                           and move.country_code == 'ES' \
                                           and move.company_id.l10n_es_sii_tax_agency \
                                           and has_tax

    def _l10n_es_is_dua(self):
        self.ensure_one()
        return any(t.l10n_es_type == 'dua' for t in self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy())

    #  Action Methods
    def action_l10n_es_send_sii(self):
        self.ensure_one()
        self._send_l10n_es_invoice()
        return {
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        }

    def button_request_cancel(self):
        # EXTENDS 'account'
        if self._l10n_es_edi_sii_need_cancel_request():
            return self._l10n_es_edi_cancel_invoice()

        return super().button_request_cancel()

    def button_draft(self):
        # EXTENDS 'account'
        for move in self:
            if move.l10n_es_edi_sii_error:
                move.l10n_es_edi_sii_error = False
        return super().button_draft()

    # Business Methods
    def _post(self, soft=True):
        # EXTENDS 'account'
        res = super()._post(soft=soft)
        self.filtered('l10n_es_edi_is_required').l10n_es_edi_sii_state = 'to_send'
        return res

    def _l10n_es_edi_sii_need_cancel_request(self):
        self.ensure_one()
        return (
            self.is_sale_document()
            and self.l10n_es_edi_sii_state == 'sent'
        )

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self._l10n_es_edi_sii_need_cancel_request()

    # Spain SII Business Methods
    def _send_l10n_es_invoice(self, cancel=False):
        self.ensure_one()
        if self.l10n_es_edi_sii_error:
            self.l10n_es_edi_sii_error = False

        # Invoice configuration validation
        errors = self._l10n_es_sii_check_move_configuration()
        if errors:
            self.l10n_es_edi_sii_error = Markup("%s<br/>%s") % (
                self.env._("Invalid invoice configuration:"),
                Markup("<br/>").join(errors)
            )
            return {'blocking_level': 'error'}

        # Generate payload
        info_list = self._l10n_es_edi_get_invoices_info()

        # Call SII web service
        res = self._l10n_es_edi_call_web_service_sign(info_list, cancel=cancel)
        if res.get('success'):
            self.l10n_es_edi_sii_state = 'sent'
            request_json = json.dumps(info_list, indent=4)
            self.env['ir.attachment'].create({
                'name': f'sii_payload_{self.name}.json',
                'raw': request_json.encode(),
                'mimetype': 'application/json',
                'res_model': self._name,
                'res_id': self.id,
                'res_field': 'l10n_es_edi_sii_json_file',
            })
            if cancel:
                self.l10n_es_edi_csv = False
                self.l10n_es_edi_sii_state = False
        else:
            if res.get('error'):
                self.l10n_es_edi_sii_error = res['error']
                if self._can_commit():
                    self.env.cr.commit()
        return res

    def _l10n_es_edi_cancel_invoice(self):
        """
        Handles the cancellation flow:
        1. Calls SII to cancel the invoice.
        2. If successful, calls the standard Odoo button_cancel.
        """
        self.ensure_one()
        res = self._send_l10n_es_invoice(cancel=True)

        if res.get('success'):
            self.l10n_es_edi_sii_state = 'cancel'
            self.message_post(body=self.env._(
                "Invoice successfully cancelled at SII (Spain Tax Agency)."
            ))
            return self.button_cancel()

        return False

    def _l10n_es_edi_call_web_service_sign(self, info_list, cancel=False):
        company = self.company_id
        csv_number = self.l10n_es_edi_csv
        error_msg = None

        if not self.l10n_es_registration_date:
            self.l10n_es_registration_date = fields.Date.context_today(self)

        l10n_es_sii_tax_agency = company.l10n_es_sii_tax_agency
        SERVICE_CONFIG_MAP = {
            'aeat': self._l10n_es_edi_web_service_aeat_vals,
            'bizkaia': self._l10n_es_edi_web_service_bizkaia_vals,
            'gipuzkoa': self._l10n_es_edi_web_service_gipuzkoa_vals,
        }
        connection_vals = SERVICE_CONFIG_MAP[l10n_es_sii_tax_agency]()

        header = {
            'IDVersionSii': '1.1',
            'Titular': {
                'NombreRazon': company.name[:120],
                'NIF': company.vat[2:] if company.vat.startswith('ES') else company.vat,
            },
            'TipoComunicacion': 'A1' if csv_number else 'A0',
        }

        with requests.Session() as session:
            try:
                session.cert = company.l10n_es_sii_certificate_id
                session.mount('https://', CertificateAdapter(ciphers=EUSKADI_CIPHERS))

                client = zeep.Client(connection_vals['url'], operation_timeout=60, timeout=60, session=session)
                if self.is_sale_document():
                    service_name = 'SuministroFactEmitidas'
                else:
                    service_name = 'SuministroFactRecibidas'
                if company.l10n_es_sii_test_env and not connection_vals.get('test_url'):
                    service_name += 'Pruebas'

                # Establish the connection.
                serv = client.bind('siiService', service_name)
                if company.l10n_es_sii_test_env and connection_vals.get('test_url'):
                    serv._binding_options['address'] = connection_vals['test_url']

                if cancel:
                    if self.is_sale_document():
                        res = serv.AnulacionLRFacturasEmitidas(header, info_list)
                    else:
                        res = serv.AnulacionLRFacturasRecibidas(header, info_list)
                else:
                    if self.is_sale_document():
                        res = serv.SuministroLRFacturasEmitidas(header, info_list)
                    else:
                        res = serv.SuministroLRFacturasRecibidas(header, info_list)
            except requests.exceptions.SSLError:
                error_msg = self.env._("The SSL certificate could not be validated.")
            except (zeep.exceptions.Error, requests.exceptions.ConnectionError) as error:
                error_msg = self.env._("Networking error:\n%s", error)
            except Exception as error:  # noqa: BLE001
                error_msg = str(error)

        if error_msg:
            return {
                'error': error_msg,
                'blocking_level': 'warning',
            }

        # Process response.
        if not res or not res.RespuestaLinea:
            return {
                'error': self.env._("The web service is not responding"),
                'blocking_level': 'warning',
            }

        resp_state = res["EstadoEnvio"]
        l10n_es_edi_csv = res['CSV']

        if resp_state == 'Correcto':
            self.write({'l10n_es_edi_csv': l10n_es_edi_csv})
            return {'success': True}

        result = {}
        for respl in res.RespuestaLinea:
            resp_line_state = respl.EstadoRegistro
            respl_dict = dict(respl)

            if resp_line_state in ('Correcto', 'AceptadoConErrores'):
                self.l10n_es_edi_csv = l10n_es_edi_csv
                result = {'success': True}
                if resp_line_state == 'AceptadoConErrores':
                    self.message_post(body=self.env._("This was accepted with errors: ") + html_escape(respl.DescripcionErrorRegistro))

            elif (
                (respl_dict.get('RegistroDuplicado') and respl.RegistroDuplicado.EstadoRegistro == 'Correcta')
                or
                (cancel and respl_dict.get('CodigoErrorRegistro') == 3001)
            ):
                result = {'success': True}
                self.message_post(body=self.env._("We saw that this invoice was sent correctly before, but we did not treat "
                                        "the response. Make sure it is not because of a wrong configuration."))

            elif respl.CodigoErrorRegistro == 1117 and not self.env.context.get('error_1117'):
                return self.with_context(error_1117=True)._send_l10n_es_invoice(cancel=cancel)

            else:
                result = {
                    'error': self.env._("[%(error_code)s] %(error_message)s",
                                        error_code=respl.CodigoErrorRegistro,
                                        error_message=respl.DescripcionErrorRegistro),
                    'blocking_level': 'error',
                }

        return result

    # -------------------------------------------------------------------------
    # JSON GENERATION & HELPERS
    # -------------------------------------------------------------------------
    def _l10n_es_sii_check_move_configuration(self):
        self.ensure_one()
        company = self.company_id
        errors = []
        _ = self.env._

        if self.env['res.partner']._is_vat_void(company.vat):
            errors.append(_("VAT number is missing on company %s.", self.company_id.display_name))

        # Certificate check
        if not company.l10n_es_sii_certificate_id:
            errors.append(_("Please configure the certificate for SII."))
        # Tax agency check
        if not company.l10n_es_sii_tax_agency:
            errors.append(_("Please specify a tax agency on your company for SII."))

        lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_subsection', 'line_note')
        )

        total_taxes = lines.mapped('tax_ids').flatten_taxes_hierarchy()
        for line in lines:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            l10n_types = taxes.mapped('l10n_es_type')

            recargo_count = l10n_types.count('recargo')
            retention_count = l10n_types.count('retencion')
            sujeto_count = l10n_types.count('sujeto')
            no_sujeto_count = l10n_types.count('no_sujeto')
            no_sujeto_loc_count = l10n_types.count('no_sujeto_loc')
            if retention_count > 1:
                errors.append(_("Line %s should only have one retention tax.", line.display_name))
            if recargo_count > 1:
                errors.append(_("Line %s should only have one recargo tax.", line.display_name))
            if sujeto_count > 1:
                errors.append(_("Line %s should only have one sujeto tax.", line.display_name))
            if no_sujeto_count > 1:
                errors.append(_("Line %s should only have one no sujeto tax.", line.display_name))
            if no_sujeto_loc_count > 1:
                errors.append(_("Line %s should only have one no sujeto (localizations) tax.", line.display_name))
            if sujeto_count + no_sujeto_loc_count + no_sujeto_count > 1:
                errors.append(_("Line %s should only have one main tax.", line.display_name))

        if (
            self.is_outbound()
            and self.commercial_partner_id._l10n_es_is_foreign()
            and total_taxes
            and not any(t.tax_scope for t in total_taxes)
        ):
            errors.append(
                _("In case of a foreign customer, you need to configure the tax scope on taxes:\n%s",
                           "\n".join(total_taxes.mapped('name')))
            )
        return errors

    def _l10n_es_edi_get_invoices_info(self):
        info_list = []
        com_partner = self.commercial_partner_id
        is_simplified = self.l10n_es_is_simplified

        info = {
            'PeriodoLiquidacion': {
                'Ejercicio': str(self.date.year),
                'Periodo': str(self.date.month).zfill(2),
            },
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': self.invoice_date.strftime('%d-%m-%Y'),
            },
        }

        if self.is_sale_document():
            invoice_node = info['FacturaExpedida'] = {}
        else:
            invoice_node = info['FacturaRecibida'] = {}

        # === Partner ===

        partner_info = com_partner._l10n_es_edi_get_partner_info()

        # === Invoice ===

        if self.delivery_date and self.delivery_date != self.invoice_date:
            invoice_node['FechaOperacion'] = self.delivery_date.strftime('%d-%m-%Y')
        invoice_node['DescripcionOperacion'] = self.invoice_origin[:500] if self.invoice_origin else 'manual'
        reagyp = self.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_type == 'sujeto_agricultura')
        if self.is_sale_document():
            nif = self.company_id.vat[2:] if self.company_id.vat.startswith('ES') else self.company_id.vat
            info['IDFactura']['IDEmisorFactura'] = {'NIF': nif}
            info['IDFactura']['NumSerieFacturaEmisor'] = self.name[:60]
            if not is_simplified:
                invoice_node['Contraparte'] = {
                    **partner_info,
                    'NombreRazon': com_partner.name[:120],
                }
            invoice_node['ClaveRegimenEspecialOTrascendencia'] = self.invoice_line_ids.tax_ids._l10n_es_get_regime_code()
        else:
            if self._l10n_es_is_dua():
                partner = self.company_id.partner_id
                partner_info = partner._l10n_es_edi_get_partner_info()
            info['IDFactura']['IDEmisorFactura'] = partner_info
            # In case of cancel
            info["IDFactura"]["IDEmisorFactura"].update(
                {"NombreRazon": com_partner.name[0:120]}
            )
            info["IDFactura"]["NumSerieFacturaEmisor"] = (self.ref or "")[:60]
            if not is_simplified:
                invoice_node['Contraparte'] = {
                    **partner_info,
                    'NombreRazon': com_partner.name[:120],
                }

            if self.l10n_es_registration_date:
                invoice_node['FechaRegContable'] = self.l10n_es_registration_date.strftime('%d-%m-%Y')
            else:
                invoice_node['FechaRegContable'] = fields.Date.context_today(self).strftime('%d-%m-%Y')

            mod_303_10 = self.env.ref('l10n_es.mod_303_casilla_10_balance')._get_matching_tags()
            mod_303_11 = self.env.ref('l10n_es.mod_303_casilla_11_balance')._get_matching_tags()
            tax_tags = self.invoice_line_ids.tax_ids.repartition_line_ids.tag_ids
            intracom = bool(tax_tags & (mod_303_10 + mod_303_11))
            if intracom:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '09'
            elif reagyp:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '02'
            else:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '01'

        if self.move_type == 'out_invoice':
            invoice_node['TipoFactura'] = 'F2' if is_simplified else 'F1'
        elif self.move_type == 'out_refund':
            invoice_node['TipoFactura'] = 'R5' if is_simplified else 'R1'
            invoice_node['TipoRectificativa'] = 'I'
        elif self.move_type == 'in_invoice':
            if reagyp:
                invoice_node['TipoFactura'] = 'F6'
            elif self._l10n_es_is_dua():
                invoice_node['TipoFactura'] = 'F5'
            else:
                invoice_node['TipoFactura'] = 'F1'
        elif self.move_type == 'in_refund':
            invoice_node['TipoFactura'] = 'R4'
            invoice_node['TipoRectificativa'] = 'I'

        # === Taxes ===

        sign = -1 if self.is_refund() else 1

        if self.is_sale_document():
            # Customer invoices
            if not com_partner._l10n_es_is_foreign() or is_simplified:
                tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info()
                invoice_node['TipoDesglose'] = {'DesgloseFactura': tax_details_info_vals['tax_details_info']}

                invoice_node['ImporteTotal'] = float_round(sign * (
                    tax_details_info_vals['tax_details']['base_amount']
                    + tax_details_info_vals['tax_details']['tax_amount']
                    - tax_details_info_vals['tax_amount_retention']
                ), 2)
            else:
                tax_details_info_service_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
                )
                tax_details_info_consu_vals = self._l10n_es_edi_get_invoices_tax_details_info(
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

                invoice_node['ImporteTotal'] = float_round(sign * (
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
                filter_invl_to_apply=lambda x: any(t for t in x.tax_ids if t.l10n_es_type == 'sujeto_isp'),
            )
            tax_details_info_other_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: not any(t for t in x.tax_ids if t.l10n_es_type == 'sujeto_isp'),
            )

            invoice_node['DesgloseFactura'] = {}
            if tax_details_info_isp_vals['tax_details_info']:
                invoice_node['DesgloseFactura']['InversionSujetoPasivo'] = tax_details_info_isp_vals['tax_details_info']
            if tax_details_info_other_vals['tax_details_info']:
                invoice_node['DesgloseFactura']['DesgloseIVA'] = tax_details_info_other_vals['tax_details_info']

            if self._l10n_es_is_dua() or any(t.l10n_es_type == 'ignore' for t in self.invoice_line_ids.tax_ids):
                invoice_node['ImporteTotal'] = float_round(sign * (
                        tax_details_info_isp_vals['tax_details']['base_amount']
                        + tax_details_info_isp_vals['tax_details']['tax_amount']
                        + tax_details_info_other_vals['tax_details']['base_amount']
                        + tax_details_info_other_vals['tax_details']['tax_amount']
                ), 2)
            else:  # Intra-community -100 repartition line needs to be taken into account
                invoice_node['ImporteTotal'] = float_round(-self.amount_total_signed
                                                     - sign * tax_details_info_isp_vals['tax_amount_retention']
                                                     - sign * tax_details_info_other_vals['tax_amount_retention'], 2)

            invoice_node['CuotaDeducible'] = float_round(sign * (
                tax_details_info_isp_vals['tax_amount_deductible']
                + tax_details_info_other_vals['tax_amount_deductible']
            ), 2)

        info_list.append(info)

        return info_list

    def _l10n_es_edi_get_invoices_tax_details_info(self, filter_invl_to_apply=None):

        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
            }

        def filter_to_apply(base_line, tax_data):
            # For intra-community, we do not take into account the negative repartition line
            return (
                not tax_data['is_reverse_charge']
                and tax_data['tax'].amount != -100.0
                and tax_data['tax'].l10n_es_type != 'ignore'
            )

        def full_filter_invl_to_apply(invoice_line):
            if set(invoice_line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type')) == {'ignore'}:
                return False
            return filter_invl_to_apply(invoice_line) if filter_invl_to_apply else True

        tax_details = self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=full_filter_invl_to_apply,
            filter_tax_values_to_apply=filter_to_apply,
            grouping_key_generator=grouping_key_generator,
        )
        sign = -1 if self.is_refund() else 1

        tax_details_info = defaultdict(dict)

        # Detect for which is the main tax for 'recargo'. Since only a single combination tax + recargo is allowed
        # on the same invoice, this can be deduced globally.

        # Mapping between main tax and recargo tax details
        # structure: {("l10n_es_type" of the main tax, amount of the main tax): {'tax_amount': float, 'applied_tax_amount': float}}
        # dict of keys: tuple ("l10n_es_type" of the main tax, amount of the main tax)
        #       values: dict of float
        recargo_tax_details = defaultdict(lambda: defaultdict(float))
        for base_line in tax_details['base_lines']:
            line = base_line['record']
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            recargo_tax = taxes.filtered(lambda t: t.l10n_es_type == 'recargo')[:1]
            if recargo_tax and taxes:
                recargo_main_tax = taxes.filtered(lambda x: x.l10n_es_type in ('sujeto', 'sujeto_isp'))[:1]
                aggregated_values = tax_details['tax_details_per_record'][line]
                recargo_values = next(iter(
                    values
                    for values in aggregated_values['tax_details'].values()
                    if (
                        values['grouping_key']
                        and values['grouping_key']['l10n_es_type'] == recargo_tax.l10n_es_type
                        and values['grouping_key']['applied_tax_amount'] == recargo_tax.amount
                    )
                ))
                recargo_tax_details[recargo_main_tax.l10n_es_type, recargo_main_tax.amount]['tax_amount'] += recargo_values['tax_amount']
                recargo_tax_details[recargo_main_tax.l10n_es_type, recargo_main_tax.amount]['applied_tax_amount'] = recargo_values['applied_tax_amount']

        tax_amount_deductible = 0.0
        tax_amount_retention = 0.0
        base_amount_not_subject = 0.0
        base_amount_not_subject_loc = 0.0
        tax_subject_info_list = []
        tax_subject_isp_info_list = []
        for tax_values in tax_details['tax_details'].values():
            recargo = recargo_tax_details.get((tax_values['l10n_es_type'], tax_values['applied_tax_amount']))
            if self.is_sale_document():
                # Customer invoices

                if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp'):
                    tax_amount_deductible += tax_values['tax_amount']

                    base_amount = sign * tax_values['base_amount']
                    tax_info = {
                        'TipoImpositivo': tax_values['applied_tax_amount'],
                        'BaseImponible': float_round(base_amount, 2),
                        'CuotaRepercutida': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                    }

                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']

                    if tax_values['l10n_es_type'] == 'sujeto':
                        tax_subject_info_list.append(tax_info)
                    else:
                        tax_subject_isp_info_list.append(tax_info)

                elif tax_values['l10n_es_type'] == 'exento':
                    tax_details_info['Sujeta'].setdefault('Exenta', {'DetalleExenta': []})
                    tax_details_info['Sujeta']['Exenta']['DetalleExenta'].append({
                        'BaseImponible': float_round(sign * tax_values['base_amount'], 2),
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

            else:
                # Vendor bills
                if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc', 'dua'):
                    tax_amount_deductible += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'retencion':
                    tax_amount_retention += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto':
                    base_amount_not_subject += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto_loc':
                    base_amount_not_subject_loc += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'ignore':
                    continue

                if tax_values['l10n_es_type'] not in ['retencion', 'recargo']:  # = in sujeto/sujeto_isp/no_deducible
                    base_amount = sign * tax_values['base_amount']
                    tax_details_info.setdefault('DetalleIVA', [])
                    tax_info = {
                        'BaseImponible': float_round(base_amount, 2),
                    }
                    if tax_values['l10n_es_type'] == 'sujeto_agricultura':
                        tax_info.update({
                            'PorcentCompensacionREAGYP': tax_values['applied_tax_amount'],
                            'ImporteCompensacionREAGYP': round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                        })
                    elif tax_values['applied_tax_amount'] > 0.0:
                        tax_info.update({
                            'TipoImpositivo': tax_values['applied_tax_amount'],
                            'CuotaSoportada': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                        })
                    if tax_values['l10n_es_bien_inversion']:
                        tax_info['BienInversion'] = 'S'
                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']
                    tax_details_info['DetalleIVA'].append(tax_info)

        if tax_subject_isp_info_list and not tax_subject_info_list:  # Only for sale_invoices
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

        if not self.company_id.currency_id.is_zero(base_amount_not_subject) and self.is_sale_document():
            tax_details_info['NoSujeta']['ImportePorArticulos7_14_Otros'] = float_round(sign * base_amount_not_subject, 2)
        if not self.company_id.currency_id.is_zero(base_amount_not_subject_loc) and self.is_sale_document():
            tax_details_info['NoSujeta']['ImporteTAIReglasLocalizacion'] = float_round(sign * base_amount_not_subject_loc, 2)
        if not tax_details_info and self.is_sale_document():
            if any(t['l10n_es_type'] == 'no_sujeto' for t in tax_details['tax_details'].values()):
                tax_details_info['NoSujeta']['ImportePorArticulos7_14_Otros'] = 0
            if any(t['l10n_es_type'] == 'no_sujeto_loc' for t in tax_details['tax_details'].values()):
                tax_details_info['NoSujeta']['ImporteTAIReglasLocalizacion'] = 0

        return {
            'tax_details_info': tax_details_info,
            'tax_details': tax_details,
            'tax_amount_deductible': tax_amount_deductible,
            'tax_amount_retention': tax_amount_retention,
            'base_amount_not_subject': base_amount_not_subject,
            'S1_list': tax_subject_info_list,  # TBAI has separate sections for S1 and S2
            'S2_list': tax_subject_isp_info_list,  # TBAI has separate sections for S1 and S2
        }

    def _l10n_es_edi_web_service_aeat_vals(self):
        if self.is_sale_document():
            return {
                'url': f'{AEAT_BASE_URL}/SuministroFactEmitidas.wsdl',
                'test_url': f'{AEAT_TEST_BASE_URL}/fe/SiiFactFEV1SOAP',
            }
        return {
            'url': f'{AEAT_BASE_URL}/SuministroFactRecibidas.wsdl',
            'test_url': f'{AEAT_TEST_BASE_URL}/fr/SiiFactFRV1SOAP',
        }

    def _l10n_es_edi_web_service_bizkaia_vals(self):
        if self.is_sale_document():
            return {
                'url': f'{BIZKAIA_BASE_URL}/SuministroFactEmitidas.wsdl',
                'test_url': f'{BIZKAIA_TEST_BASE_URL}/fe/SiiFactFEV1SOAP',
            }
        return {
            'url': f'{BIZKAIA_BASE_URL}/SuministroFactRecibidas.wsdl',
            'test_url': f'{BIZKAIA_TEST_BASE_URL}/fr/SiiFactFRV1SOAP',
        }

    def _l10n_es_edi_web_service_gipuzkoa_vals(self):
        if self.is_sale_document():
            return {
                'url': f'{GIPUZKOA_BASE_URL}/SuministroFactEmitidas.wsdl',
                'test_url': f'{GIPUZKOA_TEST_BASE_URL}/fe/SiiFactFEV1SOAP',
            }
        return {
            'url': f'{GIPUZKOA_BASE_URL}/SuministroFactRecibidas.wsdl',
            'test_url': f'{GIPUZKOA_TEST_BASE_URL}/fr/SiiFactFRV1SOAP',
        }
