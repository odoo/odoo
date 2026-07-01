import json
import random
from datetime import datetime

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cr_fe_clave = fields.Char(string="Clave FE", readonly=True, copy=False)
    l10n_cr_fe_consecutivo = fields.Char(string="Consecutivo FE", readonly=True, copy=False)
    l10n_cr_fe_xml = fields.Text(string="XML FE", readonly=True, copy=False)
    l10n_cr_fe_state = fields.Selection(
        selection=[('draft', "Borrador"), ('generated', "Generado"), ('error', "Error")],
        string="Estado FE", default='draft', readonly=True, copy=False)

    def _l10n_cr_fe_param(self, key):
        return self.env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.' + key) or ''

    def _l10n_cr_fe_build_detalles(self):
        self.ensure_one()
        cabys = self._l10n_cr_fe_param('default_cabys')
        detalles = []
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            subtotal = line.price_subtotal
            impuesto_neto = line.price_total - line.price_subtotal
            detalle = {
                'codigoCABYS': cabys,
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

    def _l10n_cr_fe_build_clave_params(self):
        self.ensure_one()
        return {
            'tipoDocumento': 'FE',
            'tipoCedula': self._l10n_cr_fe_param('emisor_tipo_identif') == '02' and 'juridico' or 'fisico',
            'cedula': self._l10n_cr_fe_param('emisor_cedula'),
            'situacion': 'normal',
            'consecutivo': str(self.id),
            'codigoSeguridad': str(random.randint(0, 99999999)).zfill(8),
            'sucursal': '001',
            'terminal': '00001',
        }

    def _l10n_cr_fe_build_genxml_params(self, clave, consecutivo, detalles):
        self.ensure_one()
        fecha = fields.Datetime.context_timestamp(self, datetime.now())
        total = self.amount_total
        base = self.amount_untaxed
        medios_pago = [{'tipoMedioPago': '01', 'totalMedioPago': total}]
        return {
            'clave': clave,
            'proveedor_sistemas': self._l10n_cr_fe_param('proveedor_sistemas'),
            'codigo_actividad_emisor': self._l10n_cr_fe_param('emisor_codigo_actividad'),
            'consecutivo': consecutivo,
            'fecha_emision': fecha.strftime('%Y-%m-%dT%H:%M:%S-06:00'),
            'emisor_nombre': self._l10n_cr_fe_param('emisor_nombre'),
            'emisor_tipo_identif': self._l10n_cr_fe_param('emisor_tipo_identif'),
            'emisor_num_identif': self._l10n_cr_fe_param('emisor_cedula'),
            'emisor_provincia': self._l10n_cr_fe_param('emisor_provincia'),
            'emisor_canton': self._l10n_cr_fe_param('emisor_canton'),
            'emisor_distrito': self._l10n_cr_fe_param('emisor_distrito'),
            'emisor_otras_senas': self._l10n_cr_fe_param('emisor_otras_senas'),
            'emisor_email': self._l10n_cr_fe_param('emisor_email'),
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
