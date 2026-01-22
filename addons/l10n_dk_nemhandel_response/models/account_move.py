from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    nemhandel_move_state = fields.Selection(selection_add=[
        ('BusinessAccept', 'Approved'),
        ('BusinessReject', 'Rejected'),
    ])
    nemhandel_response_ids = fields.One2many('nemhandel.response', 'move_id')
    nemhandel_can_send_response = fields.Boolean(compute='_compute_nemhandel_can_send_response')

    @api.depends('state', 'nemhandel_response_ids.nemhandel_state')
    def _compute_nemhandel_move_state(self):
        super()._compute_nemhandel_move_state()
        for move in self:
            valid_status = move.nemhandel_response_ids.filtered(lambda r: r.nemhandel_state == 'done').mapped('response_code')
            if not valid_status:
                continue
            move.nemhandel_move_state = valid_status[0]

    @api.depends("nemhandel_response_ids.nemhandel_state")
    def _compute_nemhandel_can_send_response(self):
        for move in self:
            move.nemhandel_can_send_response = (
                move.nemhandel_message_uuid
                and move.move_type in ('in_invoice', 'in_refund')
                and not move.nemhandel_response_ids.filtered(
                    lambda r: r.nemhandel_state == 'not_serviced' or r.nemhandel_state != 'error'
                )
                and move.partner_id.nemhandel_response_support
            )

    def _post(self, soft=True):
        res = super()._post(soft)
        self.action_nemhandel_send_approval_response()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        if action := self.action_nemhandel_open_rejection_wizard():
            action['context'] = {'cancel_res': res}
            return action
        return res

    def action_nemhandel_send_approval_response(self):
        moves_to_respond_by_company = self.filtered('nemhandel_can_send_response').grouped('company_id')
        for company in moves_to_respond_by_company:
            company.nemhandel_edi_user._nemhandel_send_response(moves_to_respond_by_company[company], 'BusinessAccept')

    def action_nemhandel_open_rejection_wizard(self):
        nemhandel_moves = self.filtered('nemhandel_can_send_response')
        if nemhandel_moves:
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Rejection response"),
                'view_mode': 'form',
                'res_model': 'nemhandel.rejection.wizard',
                'target': 'new',
                'res_id': self.env['nemhandel.rejection.wizard'].create({'move_ids': nemhandel_moves.ids}).id,
            }

    def action_open_nemhandel_reponses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Nemhandel Responses"),
            'view_mode': 'list',
            'res_model': 'nemhandel.response',
            'domain': [('id', 'in', self.nemhandel_response_ids.ids)],
        }
