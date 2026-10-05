# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools import format_list, SQL


class AccountMove(models.Model):
    _inherit = 'account.move'

    service_count = fields.Integer(compute="_compute_service_count", string='Services')

    @api.depends("line_ids.vehicle_log_service_ids")
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.line_ids.vehicle_log_service_ids)

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

    def _link_bill_origin_to_purchase_orders(self, timeout=10):
        # Read the values beforehand: the bill lines replaced by purchase order lines are deleted during the matching.
        values_before = {
            line.id: (line.move_id, line.product_id, line.vehicle_id)
            for line in self.invoice_line_ids if line.display_type == 'product'
        }
        res = super()._link_bill_origin_to_purchase_orders(timeout=timeout)
        # The bill lines matched with a purchase order were replaced by its lines: give their vehicle to the new lines.
        vehicles_per_product_per_move = defaultdict(lambda: defaultdict(set))
        for line_id in values_before.keys() - set(self.invoice_line_ids.ids):
            move, product, vehicle = values_before[line_id]
            # Empty vehicles are kept too: a product whose lines don't all share the same vehicle is ambiguous.
            vehicles_per_product_per_move[move][product].add(vehicle)
        for move, vehicles_per_product in vehicles_per_product_per_move.items():
            if not any(all_vehicles := set().union(*vehicles_per_product.values())):
                continue
            new_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product' and l.id not in values_before)
            for line in new_lines:
                vehicles = vehicles_per_product.get(line.product_id) or all_vehicles
                if len(vehicles) == 1:  # If all lines with the same product also had the same vehicle we add it
                    line.vehicle_id = next(iter(vehicles))
            if lost_vehicles := self.env['fleet.vehicle'].union(all_vehicles) - new_lines.vehicle_id:
                move._message_log(body=self.env._(
                    "Some vehicles could not be matched when updating the bill from the matched purchase order: %s",
                    format_list(self.env, lost_vehicles.sudo().mapped('display_name')),
                ))
        return res

    def action_show_services(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Services"),
            'res_model': 'fleet.vehicle.log.services',
            'domain': [
                ('account_move_line_id', 'in', self.line_ids.ids),
            ],
            "view_mode": "list,form",
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index='btree_not_null')
    # used to decide whether the vehicle_id field is editable
    need_vehicle = fields.Boolean(compute='_compute_need_vehicle')
    vehicle_log_service_ids = fields.One2many(export_string_translation=False,
        comodel_name='fleet.vehicle.log.services', inverse_name='account_move_line_id')  # One2one

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
        return SQL("%s AND (base_line.vehicle_id = tax_line.vehicle_id OR tax_line.vehicle_id IS NULL)", query)

    @api.model
    def _get_query_tax_details_aml_fields(self):
        return (*super()._get_query_tax_details_aml_fields(), 'vehicle_id')

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
