import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nCrFeProveedorEmail(models.Model):
    _name = 'l10n_cr.fe.proveedor.email'
    _inherit = ['mail.thread']
    _description = "Correo entrante de proveedor (XML de factura electrónica)"
    _order = 'id desc'
    _primary_email = 'email_from'

    email_from = fields.Char(string="Remitente", readonly=True)
    date = fields.Datetime(string="Fecha de recepción", readonly=True)
    state = fields.Selection([
        ('procesado', "Factura creada"),
        ('duplicado', "Ya existía (Clave duplicada)"),
        ('sin_xml_valido', "Sin XML válido"),
    ], string="Estado", readonly=True)
    move_id = fields.Many2one('account.move', string="Factura de proveedor", readonly=True)
    error_message = fields.Text(string="Motivo", readonly=True)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        custom_values = dict(custom_values or {})
        custom_values.setdefault('date', msg_dict.get('date'))
        return super().message_new(msg_dict, custom_values=custom_values)

    def _message_post_after_hook(self, new_message, message_values):
        res = super()._message_post_after_hook(new_message, message_values)
        self._l10n_cr_fe_procesar_adjuntos(new_message)
        return res

    def _l10n_cr_fe_procesar_adjuntos(self, message):
        self.ensure_one()
        for attachment in message.attachment_ids.filtered(
                lambda a: a.name and a.name.lower().endswith('.xml')):
            try:
                vals = self.env['account.move']._l10n_cr_fe_build_vals_from_proveedor_xml(
                    base64.b64decode(attachment.datas))
            except UserError:
                continue
            clave = vals['l10n_cr_fe_proveedor_clave']
            existing = self.env['account.move'].search(
                [('l10n_cr_fe_proveedor_clave', '=', clave)], limit=1)
            if existing:
                self.write({'state': 'duplicado', 'move_id': existing.id})
            else:
                move = self.env['account.move'].create(vals)
                self.write({'state': 'procesado', 'move_id': move.id})
            return
        self.write({
            'state': 'sin_xml_valido',
            'error_message': _("El correo no traía ningún adjunto XML de factura "
                                "electrónica válido."),
        })
