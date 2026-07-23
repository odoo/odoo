# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.tools import SQL


class AccountMove(models.Model):
    _inherit = 'account.move'

    service_count = fields.Integer(compute="_compute_service_count", string='Services')

    @api.depends("line_ids.vehicle_log_service_id")
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.line_ids.vehicle_log_service_id)

    def _post(self, soft=True):
        vendor_bill_service = self.env.ref('account_fleet.data_fleet_service_type_vendor_bill', raise_if_not_found=False)
        if not vendor_bill_service:
            return super()._post(soft)

        posted = super()._post(soft)  # We need the move name to be set, but we also need to know which move are posted for the first time.

        grouped_new_lines = defaultdict(lambda: self.env['account.move.line'])
        existing_services_map = {}

        for line in posted.line_ids:
            if not line.vehicle_id \
                    or line.move_id.move_type != 'in_invoice' \
                    or line.display_type != 'product':
                continue

            if line.vehicle_log_service_id:
                existing_services_map[line.move_id, line.vehicle_id] = line.vehicle_log_service_id
            else:
                grouped_new_lines[line.move_id, line.vehicle_id] += line

        val_list = []
        log_list = []

        for (move, vehicle), lines in grouped_new_lines.items():
            existing_service = existing_services_map.get((move, vehicle))

            if existing_service:  # Existing service => Update it instead of creating a new one
                lines.write({'vehicle_log_service_id': existing_service.id})
                labels = [name for name in lines.mapped('name') if name]
                if labels:
                    new_desc = ', '.join(labels)
                    if existing_service.description:
                        existing_service.description = f"{existing_service.description}, {new_desc}"
                    else:
                        existing_service.description = new_desc

                existing_service.message_post(
                    body=_('Additional line(s) merged from Vendor Bill: %s', move._get_html_link()),
                )
            else:  # No service => Create a new one
                val = lines[0]._prepare_fleet_log_service()

                labels = [name for name in lines.mapped('name') if name]
                val['description'] = ', '.join(labels) if labels else False
                val['account_move_line_ids'] = [Command.set(lines.ids)]

                val_list.append(val)
                log_list.append(_('Service Vendor Bill: %s', move._get_html_link()))

        if val_list:
            log_service_ids = self.env['fleet.vehicle.log.services'].create(val_list)
            for log_service_id, log in zip(log_service_ids, log_list):
                log_service_id.message_post(body=log)

        return posted

    def action_show_services(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Services"),
            'res_model': 'fleet.vehicle.log.services',
            'domain': [
                ('id', 'in', self.line_ids.vehicle_log_service_id.ids),
            ],
            "view_mode": "list,form",
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index='btree_not_null')
    # used to decide whether the vehicle_id field is editable
    need_vehicle = fields.Boolean(compute='_compute_need_vehicle')
    vehicle_log_service_id = fields.Many2one(
            comodel_name='fleet.vehicle.log.services',
            string='Fleet Service',
            copy=False,
            index='btree_not_null',
        )

    @api.depends("account_id")
    def _compute_need_vehicle(self):
        for line in self:
            line.need_vehicle = line.account_id.is_vehicle_account

    @api.model
    def _get_extra_query_base_tax_line_mapping(self) -> SQL:
        """Override to add vehicle_id matching condition for tax details query.
        This ensures that tax lines are matched with base lines having the same vehicle_id when
        both are set, while allowing the match when either side has no vehicle_id. This avoids
        inconsistencies when a single tax line is shared across base lines with mixed vehicle
        assignments (one set, one NULL).
        """
        query = super()._get_extra_query_base_tax_line_mapping()
        return SQL("%s AND (base_line.vehicle_id = account_move_line.vehicle_id OR account_move_line.vehicle_id IS NULL)", query)

    def _prepare_fleet_log_service(self):
        vendor_bill_service = self.env.ref('account_fleet.data_fleet_service_type_vendor_bill', raise_if_not_found=False)
        return {
            'service_type_id': vendor_bill_service.id,
            'vehicle_id': self.vehicle_id.id,
            'vendor_id': self.partner_id.id,
            'description': self.name,
        }

    def write(self, vals):
        if 'vehicle_id' in vals and not vals['vehicle_id']:
            self.sudo().vehicle_log_service_id.with_context(ignore_linked_bill_constraint=True).unlink()
        return super().write(vals)

    def unlink(self):
        self.sudo().vehicle_log_service_id.with_context(ignore_linked_bill_constraint=True).unlink()
        return super().unlink()
