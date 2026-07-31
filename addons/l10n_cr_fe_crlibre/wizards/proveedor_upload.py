import base64

from odoo import fields, models


class L10nCrFeProveedorUpload(models.TransientModel):
    _name = 'l10n_cr.fe.proveedor.upload'
    _description = "Cargar factura electrónica de un proveedor"

    xml_file = fields.Binary(string="Archivo XML", required=True)
    xml_filename = fields.Char(string="Nombre del archivo")

    def action_procesar(self):
        self.ensure_one()
        vals = self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(
            base64.b64decode(self.xml_file))
        invoice = self.env['account.move'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
