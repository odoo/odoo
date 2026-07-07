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


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cr_fe_clave = fields.Char(string="Clave FE", readonly=True, copy=False)
    l10n_cr_fe_consecutivo = fields.Char(string="Consecutivo FE", readonly=True, copy=False)
    l10n_cr_fe_xml = fields.Text(string="XML FE", readonly=True, copy=False)
    l10n_cr_fe_xml_firmado = fields.Text(string="XML Firmado FE", readonly=True, copy=False)
    l10n_cr_fe_respuesta_xml = fields.Text(string="Respuesta Hacienda", readonly=True, copy=False)
    l10n_cr_fe_motivo_rechazo = fields.Char(string="Motivo de rechazo", readonly=True, copy=False)
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
        return {
            'tipoDocumento': 'FE',
            'tipoCedula': config.identification_type == '02' and 'juridico' or 'fisico',
            'cedula': config.identification_number,
            'situacion': 'normal',
            'consecutivo': config.branch_number + config.terminal_number + '01' + config._l10n_cr_fe_next_consecutivo(),
            'codigoSeguridad': str(random.randint(0, 99999999)).zfill(8),
            'sucursal': config.branch_number,
            'terminal': config.terminal_number,
        }

    def _l10n_cr_fe_build_genxml_params(self, clave, consecutivo, detalles):
        self.ensure_one()
        config = self._l10n_cr_fe_get_config()
        fecha = fields.Datetime.context_timestamp(self, datetime.now())
        total = self.amount_total
        base = self.amount_untaxed
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': total}]
        return {
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
            'receptor_nombre': self.partner_id.name or '',
            'receptor_tipo_identif': '01',
            'receptor_num_identif': (self.partner_id.vat or '').replace('-', '') or '000000000',
            'condicion_venta': '01',
            'medios_pago': json.dumps(medios_pago),
            'cod_moneda': self.currency_id.name or 'CRC',
            'tipo_cambio': '1',
            'total_ventas': base,
            'total_ventas_neta': base,
            'total_comprobante': total,
            'detalles': json.dumps(detalles),
        }

    def _l10n_cr_fe_generate_and_send(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return
        if not self.partner_id:
            raise UserError(_("La factura no tiene cliente (receptor)."))

        client = self.env['l10n_cr.fe.client']
        try:
            config = self._l10n_cr_fe_get_config()
            download_code = config._l10n_cr_fe_ensure_certificate_uploaded()
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)
            detalles = self._l10n_cr_fe_build_detalles()
            genxml_params = self._l10n_cr_fe_build_genxml_params(
                clave_res['clave'], clave_res['consecutivo'], detalles)
            xml = client.gen_xml_fe(genxml_params)
            token = client.get_hacienda_token(
                config.hacienda_username, config.hacienda_password, config.environment)
            xml_firmado = client.sign_xml(download_code, config.certificate_pin, xml)
            fecha_iso = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%dT%H:%M:%S-06:00')
            client.send_fe(
                token=token, clave=clave_res['clave'], fecha_iso=fecha_iso,
                emisor_tipo=config.identification_type, emisor_num=config.identification_number,
                receptor_tipo='01',
                receptor_num=(self.partner_id.vat or '').replace('-', '') or '000000000',
                xml_firmado=xml_firmado, environment=config.environment)
        except (CrlibreApiError, UserError) as exc:
            self.l10n_cr_fe_state = 'error'
            self.message_post(body=_("Error en el flujo de Factura Electrónica: %s") % exc)
            return

        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
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
        try:
            token = client.get_hacienda_token(
                config.hacienda_username, config.hacienda_password, config.environment)
            result = client.consultar_estado(token, self.l10n_cr_fe_clave, config.environment)
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

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type == 'out_invoice':
                move._l10n_cr_fe_generate_and_send()
        return res
