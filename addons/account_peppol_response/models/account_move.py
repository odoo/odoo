from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_move_state = fields.Selection(selection_add=[
        ('AB', 'Received'),
        ('AP', 'Approved'),
        ('RE', 'Rejected'),
    ])
    peppol_response_ids = fields.One2many('account.peppol.response', 'move_id')
    peppol_can_send_response = fields.Boolean(compute='_compute_peppol_can_send_response')

    @api.depends('state', 'peppol_response_ids.peppol_state')
    def _compute_peppol_move_state(self):
        super()._compute_peppol_move_state()
        for move in self:
            valid_statuses = move.peppol_response_ids.filtered(lambda r: r.peppol_state == 'done').mapped('response_code')
            if not valid_statuses:
                continue
            if 'RE' in valid_statuses:
                move.peppol_move_state = 'RE'
            elif 'AP' in valid_statuses:
                move.peppol_move_state = 'AP'
            else:
                move.peppol_move_state = 'AB'

    @api.depends("peppol_response_ids.peppol_state")
    def _compute_peppol_can_send_response(self):
        for move in self:
            move.peppol_can_send_response = (
                move.peppol_message_uuid
                and move.move_type in ('in_invoice', 'in_refund')
                and not move.peppol_response_ids.filtered(
                    lambda r: r.peppol_state == 'not_serviced' or (r.peppol_state != 'error' and r.response_code in ('AP', 'RE'))
                )
                and move.partner_id.peppol_response_support
            )

    def _post(self, soft=True):
        res = super()._post(soft)
        self.action_peppol_send_approval_response()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        if action := self.action_peppol_open_rejection_wizard():
            action['context'] = {'cancel_res': res}
            return action
        return res

    def action_peppol_send_approval_response(self):
        moves_to_respond_by_company = self.filtered('peppol_can_send_response').grouped('company_id')
        for company in moves_to_respond_by_company:
            company.account_peppol_edi_user._peppol_send_response(moves_to_respond_by_company[company], 'AP')

    def action_peppol_open_rejection_wizard(self):
        peppol_moves = self.filtered('peppol_can_send_response')
        if peppol_moves:
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Rejection response"),
                'view_mode': 'form',
                'res_model': 'account.peppol.rejection.wizard',
                'target': 'new',
                'res_id': self.env['account.peppol.rejection.wizard'].create({'move_ids': peppol_moves.ids}).id,
            }

    def action_open_peppol_reponses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Peppol Responses"),
            'view_mode': 'list',
            'res_model': 'account.peppol.response',
            'domain': [('id', 'in', self.peppol_response_ids.ids)],
        }
