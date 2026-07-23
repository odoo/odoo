# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    account_move_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='vehicle_log_service_id',
        string='Invoice Lines',
    )
    account_move_state = fields.Selection(
        selection=lambda self: self.env['account.move']._fields['state'].selection,
        compute='_compute_account_move_state',
        string='Status',
    )
    amount = fields.Monetary(string='Cost', compute="_compute_amount", inverse="_inverse_amount",
        readonly=False, store=True, tracking=True)
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle',
        compute="_compute_vehicle_id", store=True, readonly=False, required=True)

    @api.depends('account_move_line_ids.vehicle_id')
    def _compute_vehicle_id(self):
        for service in self:
            # We avoid emptying the vehicle_id as it is a required field
            if not service.account_move_line_ids:
                continue
            service.vehicle_id = service.account_move_line_ids[0].vehicle_id

    def _inverse_amount(self):
        if any(service.account_move_line_ids for service in self):
            raise UserError(_("You cannot modify the amount of services linked to a journal item. Do it on the related accounting entry instead."))

    @api.depends('account_move_line_ids.debit')
    def _compute_amount(self):
        for log_service in self:
            log_service.amount = sum(log_service.account_move_line_ids.mapped('debit'))

    @api.depends('account_move_line_ids.parent_state')
    def _compute_account_move_state(self):
        for service in self:
            if service.account_move_line_ids:
                service.account_move_state = service.account_move_line_ids[0].parent_state
            else:
                service.account_move_state = False

    def action_open_account_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'name': _('Bill'),
            'res_id': self.account_move_line_ids[0].move_id.id if self.account_move_line_ids else False,
        }

    def action_create_account_move(self):
        self.ensure_one()

        account_move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "vehicle_id": self.vehicle_id.id,
                            "name": self.description,
                            "price_unit": self.amount,
                            "vehicle_log_service_id": self.id,
                        },
                    ),
                ],
            },
        )

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "account.move",
            "target": "current",
            "name": self.env._("Bill"),
            "res_id": account_move.id,
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_linked_bill(self):
        if self.env.context.get('ignore_linked_bill_constraint'):
            return
        if any(log_service.account_move_line_ids for log_service in self):
            raise UserError(_("You cannot delete log services records because one or more of them were bill created."))
