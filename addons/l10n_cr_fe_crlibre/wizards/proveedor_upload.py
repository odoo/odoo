import base64
import xml.etree.ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nCrFeProveedorUpload(models.TransientModel):
    _name = 'l10n_cr.fe.proveedor.upload'
    _description = "Cargar factura electrónica de un proveedor"

    xml_file = fields.Binary(string="Archivo XML", required=True)
    xml_filename = fields.Char(string="Nombre del archivo")

    def _find_text(self, node, tag):
        el = node.find('.//{*}%s' % tag)
        return el.text.strip() if el is not None and el.text else ''

    def _find_product(self, cabys):
        if not cabys:
            return self.env['product.product']
        return self.env['product.product'].search([('l10n_cr_fe_cabys', '=', cabys)], limit=1)

    def _find_tax(self, tarifa_percent):
        if not tarifa_percent:
            return self.env['account.tax']
        return self.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', tarifa_percent),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    def action_procesar(self):
        self.ensure_one()
        try:
            root = ET.fromstring(base64.b64decode(self.xml_file))
        except ET.ParseError:
            raise UserError(_("El archivo no es un XML válido."))

        clave = self._find_text(root, 'Clave')
        fecha_emision = self._find_text(root, 'FechaEmision')
        emisor_el = root.find('.//{*}Emisor')
        if emisor_el is None or not clave:
            raise UserError(_(
                "El XML no tiene los datos mínimos de un comprobante electrónico (Clave/Emisor)."))
        emisor_nombre = self._find_text(emisor_el, 'Nombre')
        emisor_cedula = self._find_text(emisor_el, 'Numero')
        emisor_email = self._find_text(emisor_el, 'CorreoElectronico')
        if not emisor_cedula:
            raise UserError(_("El XML no tiene la identificación del emisor."))

        partner = self.env['res.partner'].search([('vat', '=', emisor_cedula)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': emisor_nombre or emisor_cedula,
                'vat': emisor_cedula,
                'email': emisor_email or False,
                'company_type': 'company',
            })

        invoice_lines = []
        for linea in root.findall('.//{*}LineaDetalle'):
            cabys = self._find_text(linea, 'CodigoCABYS')
            cantidad = float(self._find_text(linea, 'Cantidad') or '0')
            precio_unitario = float(self._find_text(linea, 'PrecioUnitario') or '0')
            detalle = self._find_text(linea, 'Detalle')
            tarifa_text = self._find_text(linea, 'Tarifa')
            tarifa_percent = float(tarifa_text) if tarifa_text else 0.0
            product = self._find_product(cabys)
            tax = self._find_tax(tarifa_percent)
            invoice_lines.append((0, 0, {
                'product_id': product.id or False,
                'quantity': cantidad,
                'price_unit': precio_unitario,
                'name': detalle or (product.display_name if product else _("Completar producto")),
                'tax_ids': [(6, 0, tax.ids)],
            }))

        if not invoice_lines:
            raise UserError(_("El XML no tiene líneas de detalle."))

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'l10n_cr_fe_proveedor_clave': clave,
            'l10n_cr_fe_proveedor_fecha_emision': fecha_emision,
            'invoice_line_ids': invoice_lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
