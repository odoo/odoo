# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    payslip_ids = fields.One2many(
        comodel_name='hr.payslip',
        inverse_name='move_id',
        string='Payslips',
        readonly=True,
        copy=False,
    )
    payslip_count = fields.Integer(
        string='# of Payslips',
        compute='_compute_payslip_count',
        compute_sudo=True,
        readonly=True,
    )

    def _compute_payslip_count(self):
        for move in self:
            move.payslip_count = len(move.payslip_ids)

    def action_open_payslip(self):
        self.ensure_one()
        return_action = {
            'name': 'Payslips',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
        }
        if self.payslip_count > 1:
            return_action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.payslip_ids.ids)],
            })
        else:
            return_action.update({
                'view_mode': 'form',
                'res_id': self.payslip_ids.id,
            })

        return return_action
