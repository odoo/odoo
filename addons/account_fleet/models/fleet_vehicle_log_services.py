# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    account_move_line_id = fields.Many2one(comodel_name='account.move.line')  # One2one
    account_move_state = fields.Selection(related='account_move_line_id.parent_state')
    amount = fields.Monetary(string='Cost', compute="_compute_amount", inverse="_inverse_amount",
        readonly=False, store=True, tracking=True)
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehicle',
        compute="_compute_vehicle_id", store=True, readonly=False, required=True)

    @api.depends('account_move_line_id.vehicle_id')
    def _compute_vehicle_id(self):
        for service in self:
            # We avoid emptying the vehicle_id as it is a required field
            if not service.account_move_line_id.vehicle_id:
                continue
            service.vehicle_id = service.account_move_line_id.vehicle_id

    def _inverse_amount(self):
        if any(service.account_move_line_id for service in self):
            raise UserError(_("You cannot modify amount of services linked to an account move line. Do it on the related accounting entry instead."))

    @api.depends('account_move_line_id.price_subtotal')
    def _compute_amount(self):
        for log_service in self:
            log_service.amount = log_service.account_move_line_id.debit

    def action_open_account_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'target': 'current',
            'name': _('Bill'),
            'res_id': self.account_move_line_id.move_id.id,
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_linked_bill(self):
        if self.env.context.get('ignore_linked_bill_constraint'):
            return
        if any(log_service.account_move_line_id for log_service in self):
            raise UserError(_("You cannot delete log services records because one or more of them were bill created."))
