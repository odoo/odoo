import json
import random
from datetime import datetime

from odoo import fields, models, _
from odoo.exceptions import UserError

from .crlibre_client import CrlibreApiError


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
                detalle['impuesto'] = [{
                    'codigo': '01',
                    'codigoTarifa': '08',
                    'tarifa': 13,
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

    def action_l10n_cr_fe_generate(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            raise UserError("Solo aplica a facturas de cliente.")
        if not self.partner_id:
            raise UserError("La factura no tiene cliente (receptor).")
        client = self.env['l10n_cr.fe.client']
        try:
            clave_params = self._l10n_cr_fe_build_clave_params()
            clave_res = client.get_clave(clave_params)
            detalles = self._l10n_cr_fe_build_detalles()
            genxml_params = self._l10n_cr_fe_build_genxml_params(
                clave_res['clave'], clave_res['consecutivo'], detalles)
            xml = client.gen_xml_fe(genxml_params)
        except CrlibreApiError as exc:
            # No se lanza excepción para no romper la transacción (ver spec §5):
            # se persiste el estado de error, se informa en el chatter y se
            # devuelve una notificación no bloqueante al usuario.
            self.l10n_cr_fe_state = 'error'
            self.message_post(body="Error al generar el comprobante FE: %s" % exc)
            return self._l10n_cr_fe_notify(
                "Error al generar el comprobante", str(exc), 'danger')
        self.write({
            'l10n_cr_fe_clave': clave_res['clave'],
            'l10n_cr_fe_consecutivo': clave_res['consecutivo'],
            'l10n_cr_fe_xml': xml,
            'l10n_cr_fe_state': 'generado',
        })
        self.message_post(body="Comprobante FE generado (PoC). Clave: %s" % clave_res['clave'])
        return self._l10n_cr_fe_notify(
            "Comprobante generado", "Clave: %s" % clave_res['clave'], 'success')

    def _l10n_cr_fe_notify(self, title, message, notif_type):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,  # 'success' | 'warning' | 'danger'
                'sticky': False,
            },
        }
