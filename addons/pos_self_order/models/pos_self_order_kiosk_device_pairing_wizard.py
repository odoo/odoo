from odoo import models, fields, _

POS_MANAGER_GROUP = 'point_of_sale.group_pos_manager'


class PosSelfOrderKioskDevicePairingWizard(models.TransientModel):
    _name = 'pos_self_order.kiosk.device_pairing.wizard'
    _description = "Kiosk Device Pairing Wizard"

    is_done = fields.Boolean(default=False)
    pairing_code = fields.Char(string="Pairing code", required=True)
    pairing_request_id = fields.Many2one('pos_self_order.kiosk.pairing.request', readonly=True)

    def action_confirm(self):
        self.ensure_one()

        req = self.env['pos_self_order.kiosk.pairing.request'].search([
            ('pairing_code', '=', self.pairing_code.replace(' ', '').strip()),
        ], limit=1)

        if not req or req.is_expired():
            self.pairing_request_id = None
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Invalid or expired pairing code") if not req else _("Expired pairing code"),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        if not req.approved:
            self.env['pos_self_order.kiosk.device']._create_from_pairing(req)

        self.is_done = True
        self.pairing_request_id = req.id
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Kiosk Device successfully paired"),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
