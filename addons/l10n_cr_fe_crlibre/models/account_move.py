import base64
import json
import random
import xml.etree.ElementTree as ET
from datetime import datetime

from odoo import fields, models, _
from odoo.exceptions import UserError

from .crlibre_client import CrlibreApiError


# Códigos de tarifa de IVA del catálogo de Hacienda (Anexos v4.4), por porcentaje.
L10N_CR_FE_TARIFA_IVA_CODES = {
    0: '01',
    1: '02',
    2: '03',
    4: '04',
    13: '08',
}

# Qué tipo de comprobante Hacienda genera este módulo, por move_type de Odoo.
# 'clave': valor de tipoDocumento para el endpoint w=clave.
# 'consecutivo_codigo': prefijo de 2 dígitos del consecutivo (Anexo v4.4: 01=FE, 03=NC).
# 'gen_xml_action': método de CrlibreFeClient a invocar para generar el XML.
L10N_CR_FE_TIPO_DOCUMENTO = {
    'out_invoice': {'clave': 'FE', 'consecutivo_codigo': '01', 'gen_xml_action': 'gen_xml_fe'},
    'out_refund': {'clave': 'NC', 'consecutivo_codigo': '03', 'gen_xml_action': 'gen_xml_nc'},
}

# Tiquete Electronico (TE): comparte move_type 'out_invoice' con Factura, asi que
# no puede tener su propia entrada en L10N_CR_FE_TIPO_DOCUMENTO (indexado por
# move_type). Se resuelve aparte en _l10n_cr_fe_get_tipo_documento_info().
L10N_CR_FE_TIPO_DOCUMENTO_TE = {'clave': 'TE', 'consecutivo_codigo': '04', 'gen_xml_action': 'gen_xml_te'}

# Mensaje Receptor (MR): respuesta obligatoria de Hacienda cuando esta empresa
# recibe una factura electronica de un proveedor. Cada decision (aceptar
# total, aceptar parcial, rechazar) es su propio tipo de documento con su
# propio consecutivo independiente (Anexo v4.4): 05=CCE (aceptacion total),
# 06=CPCE (aceptacion parcial), 07=RCE (rechazo). Se resuelve por
# l10n_cr_fe_mr_decision, no por move_type, en _l10n_cr_fe_get_tipo_documento_info().
L10N_CR_FE_TIPO_DOCUMENTO_MR = {
    'aceptado': {'clave': 'CCE', 'consecutivo_codigo': '05', 'gen_xml_action': 'gen_xml_mr'},
    'aceptado_parcial': {'clave': 'CPCE', 'consecutivo_codigo': '06', 'gen_xml_action': 'gen_xml_mr'},
    'rechazado': {'clave': 'RCE', 'consecutivo_codigo': '07', 'gen_xml_action': 'gen_xml_mr'},
}

# Motivos de negocio para una nota de crédito, mostrados al usuario en el asistente
# de reversión. Cada uno mapea a un código oficial de Hacienda (ver L10N_CR_FE_MOTIVO_CODIGO_MAP).
L10N_CR_FE_MOTIVO_NC = [
    ('anulacion_total', "Anulación total"),
    ('correccion_monto', "Corrección de monto, precio, cantidad o descuento"),
    ('devolucion_mercancia', "Devolución de mercancía"),
    ('referencia_otro_documento', "Referencia a otro documento"),
    ('otros', "Otros"),
]

L10N_CR_FE_MOTIVO_CODIGO_MAP = {
    'anulacion_total': '01',
    'correccion_monto': '02',
    'devolucion_mercancia': '06',
    'referencia_otro_documento': '04',
    'otros': '99',
}

# Catálogo completo de "Código de referencia" de Hacienda v4.4 (CodigoReferenciaType
# en NotaCreditoElectronica_V4.4.xsd), para selección avanzada por usuarios contables.
L10N_CR_FE_CODIGO_REFERENCIA = [
    ('01', "01 - Anula documento de referencia"),
    ('02', "02 - Corrige texto de documento de referencia"),
    ('04', "04 - Referencia a otro documento"),
    ('05', "05 - Sustituye comprobante provisional por contingencia"),
    ('06', "06 - Devolución de mercancía"),
    ('07', "07 - Sustituye comprobante electrónico"),
    ('08', "08 - Factura Endosada"),
    ('09', "09 - Nota de crédito financiera"),
    ('10', "10 - Nota de débito financiera"),
    ('11', "11 - Proveedor No Domiciliado"),
    ('12', "12 - Crédito por exoneración posterior a la facturación"),
    ('99', "99 - Otros"),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cr_fe_clave = fields.Char(string="Clave FE", readonly=True, copy=False)
    l10n_cr_fe_consecutivo = fields.Char(string="Consecutivo FE", readonly=True, copy=False)
    l10n_cr_fe_fecha_emision = fields.Char(string="Fecha de emisión FE", readonly=True, copy=False)
    l10n_cr_fe_xml = fields.Text(string="XML FE", readonly=True, copy=False)
    l10n_cr_fe_xml_firmado = fields.Text(string="XML Firmado FE", readonly=True, copy=False)
    l10n_cr_fe_respuesta_xml = fields.Text(string="Respuesta Hacienda", readonly=True, copy=False)
    l10n_cr_fe_motivo_rechazo = fields.Char(string="Motivo de rechazo", readonly=True, copy=False)
    l10n_cr_fe_motivo = fields.Selection(
        L10N_CR_FE_MOTIVO_NC, string="Motivo de la nota de crédito", copy=False)
    l10n_cr_fe_codigo_referencia = fields.Selection(
        L10N_CR_FE_CODIGO_REFERENCIA, string="Código de referencia Hacienda", copy=False)
    l10n_cr_fe_razon = fields.Char(string="Razón (Hacienda)", copy=False)
    l10n_cr_fe_es_tiquete = fields.Boolean(
        string="Consumidor final (Tiquete Electrónico)", copy=False,
        help="Si está marcado, este comprobante se emite ante Hacienda como Tiquete "
             "Electrónico (sin identificar al receptor) en vez de Factura Electrónica.")
    l10n_cr_fe_mr_decision = fields.Selection(
        selection=[
            ('aceptado', "Aceptado"),
            ('aceptado_parcial', "Aceptado parcialmente"),
            ('rechazado', "Rechazado"),
        ],
        string="Decisión sobre la factura del proveedor", copy=False)
    l10n_cr_fe_mr_motivo = fields.Char(string="Motivo (Mensaje Receptor)", copy=False)
    l10n_cr_fe_proveedor_clave = fields.Char(string="Clave de la factura del proveedor", readonly=True, copy=False)
    l10n_cr_fe_proveedor_fecha_emision = fields.Char(string="Fecha de emisión (proveedor)", readonly=True, copy=False)
    l10n_cr_fe_state = fields.Selection(
        selection=[
            ('draft', "Borrador"),
            ('generado', "Generado"),
            ('enviado', "Enviado"),
            ('aceptado', "Aceptado"),
            ('rechazado', "Rechazado"),
            ('error', "Error"),
        ],
        string="Estado FE", default='draft', readonly=True, copy=False)

    def _l10n_cr_fe_get_config(self):
        self.ensure_one()
        return self.env['l10n_cr.fe.config']._get_for_company(self.company_id)

    def _l10n_cr_fe_get_tipo_documento_info(self):
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.l10n_cr_fe_es_tiquete:
            return L10N_CR_FE_TIPO_DOCUMENTO_TE
        if self.move_type == 'in_invoice':
            return L10N_CR_FE_TIPO_DOCUMENTO_MR.get(self.l10n_cr_fe_mr_decision)
        return L10N_CR_FE_TIPO_DOCUMENTO.get(self.move_type)

    def _l10n_cr_fe_build_detalles(self):
        self.ensure_one()
        detalles = []
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            if not line.product_id.l10n_cr_fe_cabys:
                raise UserError(
                    _("El producto '%s' no tiene código CABYS configurado.") % line.product_id.display_name)
            subtotal = line.price_subtotal
            impuesto_neto = line.price_total - line.price_subtotal
            detalle = {
                'codigoCABYS': line.product_id.l10n_cr_fe_cabys,
                'cantidad': line.quantity,
                'unidadMedida': 'Unid',
                'detalle': line.name or (line.product_id.display_name or 'Producto'),
                'precioUnitario': line.price_unit,
                'montoTotal': line.price_unit * line.quantity,
                'subTotal': subtotal,
                'baseImponible': subtotal,
                'impuestoAsumidoEmisorFabrica': 0,
                'impuestoNeto': impuesto_neto,
                'montoTotalLinea': line.price_total,
            }
            if impuesto_neto:
                tarifa = int(round(line.tax_ids[:1].amount))
                codigo_tarifa = L10N_CR_FE_TARIFA_IVA_CODES.get(tarifa)
                if not codigo_tarifa:
                    raise UserError(
                        _("La tarifa de impuesto %s%% del producto '%s' no está soportada por Hacienda.")
                        % (tarifa, line.product_id.display_name))
                detalle['impuesto'] = [{
                    'codigo': '01',
                    'codigoTarifa': codigo_tarifa,
                    'tarifa': tarifa,
                    'monto': impuesto_neto,
                }]
            detalles.append(detalle)
        return detalles

    def _l10n_cr_fe_param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.' + key) or ''

    def _l10n_cr_fe_build_clave_params(self):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        tipo_doc = self._l10n_cr_fe_get_tipo_documento_info()
        return {
            'tipoDocumento': tipo_doc['clave'],
            'tipoCedula': config.identification_type == '02' and 'juridico' or 'fisico',
            'cedula': config.identification_number,
            'situacion': 'normal',
            'consecutivo': config._l10n_cr_fe_next_consecutivo(tipo_doc['consecutivo_codigo']),
            'codigoSeguridad': str(random.randint(0, 99999999)).zfill(8),
            'sucursal': config.branch_number,
            'terminal': config.terminal_number,
        }

    def _l10n_cr_fe_build_resumen_totals(self, detalles):
        """Calcula los totales de ResumenFactura a partir del detalle de líneas.

        Hacienda valida que TotalVenta/TotalGravado/TotalImpuesto/TotalComprobante
        sean consistentes entre sí y con el detalle; se derivan todos del mismo
        origen (detalles) para evitar descuadres por redondeo.
        """
        total_merc_gravada = sum(d['subTotal'] for d in detalles if d['impuestoNeto'])
        total_merc_exenta = sum(d['subTotal'] for d in detalles if not d['impuestoNeto'])
        total_impuestos = sum(d['impuestoNeto'] for d in detalles)
        total_venta = total_merc_gravada + total_merc_exenta

        desglose = {}
        for d in detalles:
            for imp in d.get('impuesto', []):
                key = (imp['codigo'], imp['codigoTarifa'])
                desglose[key] = desglose.get(key, 0) + imp['monto']
        total_desglose_impuesto = [
            {'Codigo': codigo, 'CodigoTarifaIVA': tarifa, 'TotalMontoImpuesto': monto}
            for (codigo, tarifa), monto in desglose.items()
        ]

        return {
            'total_merc_gravada': total_merc_gravada,
            'total_merc_exenta': total_merc_exenta,
            'total_gravados': total_merc_gravada,
            'total_exento': total_merc_exenta,
            'total_ventas': total_venta,
            'total_ventas_neta': total_venta,
            'totalDesgloseImpuesto': json.dumps(total_desglose_impuesto),
            'total_impuestos': total_impuestos,
            'total_comprobante': total_venta + total_impuestos,
        }

    def _l10n_cr_fe_build_genxml_params(self, clave, consecutivo, detalles):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        fecha = fields.Datetime.context_timestamp(self, datetime.now())

        if self._l10n_cr_fe_get_tipo_documento_info() != L10N_CR_FE_TIPO_DOCUMENTO_TE and not self.partner_id.vat:
            raise UserError(
                _("El cliente '%s' no tiene cédula/identificación configurada. Hacienda "
                  "rechaza los comprobantes si el receptor no tiene un número de "
                  "identificación válido.") % self.partner_id.name)

        resumen = self._l10n_cr_fe_build_resumen_totals(detalles)
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': resumen['total_comprobante']}]
        params = {
            'clave': clave,
            'proveedor_sistemas': config.identification_number,
            'codigo_actividad_emisor': config.economic_activity_code,
            'consecutivo': consecutivo,
            'fecha_emision': fecha.strftime('%Y-%m-%dT%H:%M:%S-06:00'),
            'emisor_nombre': config.legal_name,
            'emisor_tipo_identif': config.identification_type,
            'emisor_num_identif': config.identification_number,
            'emisor_provincia': config.province,
            'emisor_canton': config.canton,
            'emisor_distrito': config.district,
            'emisor_otras_senas': config.address_detail,
            'emisor_email': config.email,
            'condicion_venta': '01',
            'medios_pago': json.dumps(medios_pago),
            'cod_moneda': self.currency_id.name or 'CRC',
            'tipo_cambio': '1',
            'detalles': json.dumps(detalles),
            **resumen,
        }
        if self._l10n_cr_fe_get_tipo_documento_info() == L10N_CR_FE_TIPO_DOCUMENTO_TE:
            params['omitir_receptor'] = 'true'
        else:
            params['receptor_nombre'] = self.partner_id.name or ''
            params['receptor_tipo_identif'] = self.partner_id.l10n_cr_fe_identification_type or '01'
            params['receptor_num_identif'] = self.partner_id.vat.replace('-', '').strip()
        if self.move_type == 'out_refund':
            original = self.reversed_entry_id
            params['informacion_referencia'] = json.dumps([{
                'tipoDoc': '01',  # Factura electrónica (catálogo TipoDocReferenciaType)
                'numero': original.l10n_cr_fe_clave,
                'fechaEmision': original.l10n_cr_fe_fecha_emision,
                'codigo': self.l10n_cr_fe_codigo_referencia,
                'razon': self.l10n_cr_fe_razon or '',
            }])
        return params

    def _l10n_cr_fe_build_mr_params(self, consecutivo):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        mensaje_codigo = {'aceptado': '1', 'aceptado_parcial': '2', 'rechazado': '3'}[self.l10n_cr_fe_mr_decision]
        return {
            'clave': self.l10n_cr_fe_proveedor_clave,
            'numero_cedula_emisor': (self.partner_id.vat or '').replace('-', '').strip(),
            'fecha_emision_doc': self.l10n_cr_fe_proveedor_fecha_emision,
            'mensaje': mensaje_codigo,
            'detalle_mensaje': self.l10n_cr_fe_mr_motivo or '',
            'monto_total_impuesto': self.amount_tax,
            'codigo_actividad': config.economic_activity_code,
            'total_factura': self.amount_total,
            'numero_cedula_receptor': config.identification_number,
            'numero_consecutivo_receptor': consecutivo,
        }

    def _l10n_cr_fe_generate_and_send(self):
        self.ensure_one()
        tipo_doc = self._l10n_cr_fe_get_tipo_documento_info()
        if not tipo_doc:
            return
        if self.move_type == 'in_invoice' and self.l10n_cr_fe_state not in ('draft', 'error'):
            return
        if not self.partner_id:
            raise UserError(_("El comprobante no tiene cliente (receptor)."))
        if self.move_type == 'in_invoice':
            if not self.l10n_cr_fe_proveedor_clave or not self.l10n_cr_fe_proveedor_fecha_emision:
                raise UserError(_(
                    "La factura del proveedor no tiene clave/fecha de emisión del XML original."))
            if self.l10n_cr_fe_mr_decision in ('aceptado_parcial', 'rechazado') and not self.l10n_cr_fe_mr_motivo:
                raise UserError(_("Debes indicar el motivo del Mensaje Receptor."))

        client = self.env['l10n_cr.fe.client']
        try:
            if self.move_type == 'out_refund':
                original = self.reversed_entry_id
                if not original or original.l10n_cr_fe_state != 'aceptado':
                    raise UserError(_(
                        "No se puede generar la nota de crédito: la factura original "
                        "aún no ha sido aceptada por Hacienda."))
                if original.l10n_cr_fe_es_tiquete:
                    raise UserError(_(
                        "No se puede generar una nota de crédito sobre un Tiquete "
                        "Electrónico todavía — esta corrección no está soportada."))

            config = self._l10n_cr_fe_get_config()
            download_code = config._l10n_cr_fe_ensure_certificate_uploaded()
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)

            if self.move_type == 'in_invoice':
                mr_params = self._l10n_cr_fe_build_mr_params(clave_res['consecutivo'])
                xml = client.gen_xml_mr(mr_params)
                token = client.get_hacienda_token(
                    config.hacienda_username, config.hacienda_password, config.environment)
                xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
                client.send_mr(
                    token=token, clave=self.l10n_cr_fe_proveedor_clave,
                    fecha_iso=self.l10n_cr_fe_proveedor_fecha_emision,
                    emisor_tipo=self.partner_id.l10n_cr_fe_identification_type or '01',
                    emisor_num=(self.partner_id.vat or '').replace('-', '').strip(),
                    receptor_tipo=config.identification_type, receptor_num=config.identification_number,
                    consecutivo_receptor=clave_res['consecutivo'],
                    xml_firmado=xml_firmado, environment=config.environment)
                fecha_iso = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%dT%H:%M:%S-06:00')
            else:
                detalles = self._l10n_cr_fe_build_detalles()
                genxml_params = self._l10n_cr_fe_build_genxml_params(
                    clave_res['clave'], clave_res['consecutivo'], detalles)
                gen_xml_action = tipo_doc['gen_xml_action']
                xml = getattr(client, gen_xml_action)(genxml_params)
                token = client.get_hacienda_token(
                    config.hacienda_username, config.hacienda_password, config.environment)
                xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
                if tipo_doc == L10N_CR_FE_TIPO_DOCUMENTO_TE:
                    receptor_tipo, receptor_num = '', ''
                else:
                    receptor_tipo = self.partner_id.l10n_cr_fe_identification_type or '01'
                    receptor_num = self.partner_id.vat.replace('-', '').strip()
                fecha_iso = genxml_params['fecha_emision']
                client.send_fe(
                    token=token, clave=clave_res['clave'], fecha_iso=fecha_iso,
                    emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                    receptor_tipo=receptor_tipo, receptor_num=receptor_num,
                    xml_firmado=xml_firmado, environment=config.environment)
        except (CrlibreApiError, UserError) as exc:
            self.l10n_cr_fe_state = 'error'
            self.message_post(body=_("Error en el flujo de Factura Electrónica: %s") % exc)
            return

        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
            'l10n_cr_fe_fecha_emision': fecha_iso,
            'l10n_cr_fe_xml': xml,
            'l10n_cr_fe_xml_firmado': xml_firmado,
            'l10n_cr_fe_state': 'enviado',
        })
        self.message_post(body=_("Comprobante FE enviado a Hacienda. Clave: %s") % clave_res['clave'])

    def _l10n_cr_fe_parse_motivo(self, respuesta_xml):
        if not respuesta_xml:
            return False
        try:
            root = ET.fromstring(respuesta_xml)
        except ET.ParseError:
            return respuesta_xml[:200]
        detalle = root.find('.//DetalleMensaje')
        return detalle.text if detalle is not None else respuesta_xml[:200]

    def _l10n_cr_fe_send_acceptance_email(self):
        self.ensure_one()
        if not self.partner_id.email:
            return
        attachment_ids = []
        attachment_model = self.env['ir.attachment']
        if self.l10n_cr_fe_xml_firmado:
            attachment_ids.append(attachment_model.create({
                'name': 'comprobante_%s.xml' % (self.l10n_cr_fe_clave or self.id),
                'datas': base64.b64encode(self.l10n_cr_fe_xml_firmado.encode('utf-8')),
                'res_model': 'account.move', 'res_id': self.id,
            }).id)
        if self.l10n_cr_fe_respuesta_xml:
            attachment_ids.append(attachment_model.create({
                'name': 'respuesta_hacienda_%s.xml' % (self.l10n_cr_fe_clave or self.id),
                'datas': base64.b64encode(self.l10n_cr_fe_respuesta_xml.encode('utf-8')),
                'res_model': 'account.move', 'res_id': self.id,
            }).id)
        template = self.env.ref('l10n_cr_fe_crlibre.mail_template_l10n_cr_fe_aceptado')
        template.send_mail(self.id, force_send=True,
                            email_values={'attachment_ids': [(6, 0, attachment_ids)]})

    def action_l10n_cr_fe_consultar_estado(self):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        client = self.env['l10n_cr.fe.client']
        # Para un Mensaje Receptor (in_invoice), Hacienda rastrea el envio por la
        # clave de la factura original del proveedor (la que se manda en el sobre
        # de sendMensaje), no por la clave propia que generamos para el
        # consecutivo del Mensaje Receptor. Verificado contra el sandbox real.
        clave = self.l10n_cr_fe_proveedor_clave if self.move_type == 'in_invoice' else self.l10n_cr_fe_clave
        try:
            token = client.get_hacienda_token(
                config.hacienda_username, config.hacienda_password, config.environment)
            result = client.consultar_estado(token, clave, config.environment)
        except CrlibreApiError as exc:
            self.message_post(body=_("Error al consultar el estado FE: %s") % exc)
            return

        respuesta_xml = False
        if result.get('respuesta_xml'):
            respuesta_xml = base64.b64decode(result['respuesta_xml']).decode('utf-8')

        estado = result['ind_estado']
        if estado == 'aceptado':
            self.write({'l10n_cr_fe_state': 'aceptado', 'l10n_cr_fe_respuesta_xml': respuesta_xml})
            self.message_post(body=_("Hacienda aceptó el comprobante FE."))
            try:
                self._l10n_cr_fe_send_acceptance_email()
            except Exception as exc:
                self.message_post(body=_("No se pudo enviar el correo de notificación al cliente: %s") % exc)
        elif estado == 'rechazado':
            self.write({
                'l10n_cr_fe_state': 'rechazado',
                'l10n_cr_fe_respuesta_xml': respuesta_xml,
                'l10n_cr_fe_motivo_rechazo': self._l10n_cr_fe_parse_motivo(respuesta_xml) or _("Rechazado por Hacienda"),
            })
            self.message_post(body=_("Hacienda rechazó el comprobante FE."))
        else:
            self.message_post(body=_("Hacienda aún no tiene una respuesta definitiva (estado: %s).") % estado)

    def action_l10n_cr_fe_reintentar(self):
        self.ensure_one()
        self.write({
            'l10n_cr_fe_state': 'draft',
            'l10n_cr_fe_motivo_rechazo': False,
        })
        self._l10n_cr_fe_generate_and_send()

    def action_l10n_cr_fe_aceptar_total(self):
        self.ensure_one()
        self.l10n_cr_fe_mr_decision = 'aceptado'
        self.action_post()

    def action_l10n_cr_fe_aceptar_parcial(self):
        self.ensure_one()
        if not self.l10n_cr_fe_mr_motivo:
            raise UserError(_("Debes indicar el motivo de la aceptación parcial."))
        self.l10n_cr_fe_mr_decision = 'aceptado_parcial'
        self.action_post()

    def action_l10n_cr_fe_rechazar(self):
        self.ensure_one()
        if not self.l10n_cr_fe_mr_motivo:
            raise UserError(_("Debes indicar el motivo del rechazo."))
        self.l10n_cr_fe_mr_decision = 'rechazado'
        self._l10n_cr_fe_generate_and_send()

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move._l10n_cr_fe_get_tipo_documento_info():
                move._l10n_cr_fe_generate_and_send()
        return res
