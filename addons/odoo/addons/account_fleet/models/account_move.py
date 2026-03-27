# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        vendor_bill_service = self.env.ref('account_fleet.data_fleet_service_type_vendor_bill', raise_if_not_found=False)
        if not vendor_bill_service:
            return super()._post(soft)

        val_list = []
        log_list = []
        posted = super()._post(soft)  # We need the move name to be set, but we also need to know which move are posted for the first time.
        for line in posted.line_ids:
            if not line.vehicle_id or line.vehicle_log_service_ids\
                    or line.move_id.move_type != 'in_invoice'\
                    or line.display_type != 'product':
                continue
            val = line._prepare_fleet_log_service()
            log = _('Service Vendor Bill: %s', line.move_id._get_html_link())
            val_list.append(val)
            log_list.append(log)
        log_service_ids = self.env['fleet.vehicle.log.services'].create(val_list)
        for log_service_id, log in zip(log_service_ids, log_list):
            log_service_id.message_post(body=log)
        return posted


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index='btree_not_null')
    # used to decide whether the vehicle_id field is editable
    need_vehicle = fields.Boolean(compute='_compute_need_vehicle')
    vehicle_log_service_ids = fields.One2many(export_string_translation=False,
        comodel_name='fleet.vehicle.log.services', inverse_name='account_move_line_id')  # One2one

    def _compute_need_vehicle(self):
        self.need_vehicle = False

    def _prepare_fleet_log_service(self):
        vendor_bill_service = self.env.ref('account_fleet.data_fleet_service_type_vendor_bill', raise_if_not_found=False)
        return {
            'service_type_id': vendor_bill_service.id,
            'vehicle_id': self.vehicle_id.id,
            'vendor_id': self.partner_id.id,
            'description': self.name,
            'account_move_line_id': self.id,
        }

    def write(self, vals):
        if 'vehicle_id' in vals and not vals['vehicle_id']:
            self.sudo().vehicle_log_service_ids.with_context(ignore_linked_bill_constraint=True).unlink()
        return super().write(vals)

    def unlink(self):
        self.sudo().vehicle_log_service_ids.with_context(ignore_linked_bill_constraint=True).unlink()
        return super().unlink()
