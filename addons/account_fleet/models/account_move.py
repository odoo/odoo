# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_list, SQL


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

        vehicle_lines = posted.line_ids.filtered(
            lambda line: line.vehicle_id and line.move_id.move_type == 'in_invoice' and line.display_type == 'product'
        )
        val_list = []

        for (move, vehicle), lines in vehicle_lines.grouped(lambda line: (line.move_id, line.vehicle_id)).items():
            new_lines = lines.filtered(lambda line: not line.vehicle_log_service_id)
            if not new_lines:
                continue

            # [:1]: the bills posted before services were grouped have a service per line
            existing_service = lines.vehicle_log_service_id[:1]

            if existing_service:  # Existing service => Update it instead of creating a new one
                new_lines.write({'vehicle_log_service_id': existing_service.id})
                existing_service.message_post(
                    body=self.env._('Additional line(s) merged from Vendor Bill: %s', move._get_html_link()),
                )
            else:  # No service => Create a new one
                val_list.append({
                    'service_type_id': vendor_bill_service.id,
                    'vehicle_id': vehicle.id,
                    'company_id': move.company_id.id,
                    'vendor_id': move.commercial_partner_id.id,
                    'account_move_line_ids': [Command.set(new_lines.ids)],
                })

        for service in self.env['fleet.vehicle.log.services'].create(val_list):
            service.message_post(body=self.env._('Service Vendor Bill: %s', service.account_move_line_ids.move_id._get_html_link()))

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
            'name': self.env._("Services"),
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
        return SQL("%s AND (base_line.vehicle_id = tax_line.vehicle_id OR tax_line.vehicle_id IS NULL)", query)

    @api.model
    def _get_query_tax_details_aml_fields(self):
        return (*super()._get_query_tax_details_aml_fields(), 'vehicle_id')

    @api.constrains('vehicle_id', 'vehicle_log_service_id')
    def _check_service_vehicle_match(self):
        for line in self:
            if line.vehicle_log_service_id and line.vehicle_id != line.vehicle_log_service_id.vehicle_id:
                raise ValidationError(self.env._("The vehicle on the invoice line must match the vehicle on the linked fleet service."))

    @api.constrains('move_id', 'vehicle_log_service_id')
    def _check_service_single_bill(self):
        for line in self:
            if len(line.vehicle_log_service_id.account_move_line_ids.move_id) > 1:
                raise ValidationError(self.env._("The invoice lines of a fleet service must all belong to the same bill."))

    def write(self, vals):
        """
        When the `vehicle_id` is changed or cleared on lines linked to a fleet service:
        - If the service has no other lines, we keep it and its vehicle is changed.
            - It is archived instead if the vehicle is cleared, or if the bill already has a
            service for the new vehicle (the lines join that one on post).
        - Otherwise, the service keeps its other lines, and the changed lines are linked on post
        to the bill's service for their new vehicle, or to a new one.
        """

        if 'vehicle_id' not in vals:
            return super().write(vals)

        # The lines whose `vehicle_id` is changed or cleared leave their fleet service.

        new_vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])

        changed_lines = self.filtered(
            lambda line: line.vehicle_log_service_id and line.vehicle_id != new_vehicle,
        )

        # Remember the service of each line before disconnecting them
        lines_by_service = changed_lines.grouped('vehicle_log_service_id')

        # Disconnect before writing the new vehicle, otherwise the vehicle constraints would raise
        changed_lines.vehicle_log_service_id = False

        res = super().write(vals)

        # The services left without lines follow them to their new vehicle or are archived.
        for service, lines in lines_by_service.items():
            # sudo: the user editing the bill may not have access to the fleet services
            if service.sudo().account_move_line_ids:
                continue

            vehicles_with_service = lines.move_id.line_ids.filtered('vehicle_log_service_id').vehicle_id

            if new_vehicle and new_vehicle not in vehicles_with_service:
                lines.vehicle_log_service_id = service
            else:
                # sudo: the user editing the bill may not be allowed to modify the fleet services
                service_sudo = service.sudo()
                service_sudo.action_archive()
                service_sudo.message_post(
                    body=self.env._(
                        'Archiving record because the vehicle of its invoice lines was changed on bill %s',
                        lines.move_id._get_html_link(title=lines.move_id.name),
                    ),
                )

        return res

    def unlink(self):
        services = self.vehicle_log_service_id
        res = super().unlink()
        # sudo: the user editing the bill may not have access to the fleet services
        services.sudo().filtered(lambda service: not service.account_move_line_ids).unlink()
        return res
