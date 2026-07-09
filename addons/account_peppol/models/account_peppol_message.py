from odoo import api, fields, models


class AccountPeppolMessage(models.Model):
    _name = 'account.peppol.message'
    _description = "A Peppol message. That message can be a main document (invoice) or a business response."

    uuid = fields.Char(string='Peppol message ID', copy=False)
    state = fields.Selection(
        selection=[
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('not_serviced', 'Not Serviced'),
        ],
        string='Peppol status',
        readonly=True,
    )
    response_code = fields.Selection(
        selection=[
            ('AB', 'Acknowledged'),
            ('IP', 'In Process'),
            ('UQ', 'Under query'),
            ('CA', 'Conditionally accepted'),
            ('RE', 'Rejection'),
            ('AP', 'Approval'),
            ('PD', 'Paid'),
        ],
        compute='_compute_response_code', store=True,
        help="Code for responses."
            " Can be the code embedded in the message (for a Response message) or the most relevent response code (for an original message).",
    )
    origin_message_id = fields.Many2one(
        'account.peppol.message',
        ondelete='cascade',
        readonly=True,
        help='Contains the original message for response messages, and False for original messages.',
    )
    response_ids = fields.One2many('account.peppol.message', 'origin_message_id', readonly=True)
    move_id = fields.Many2one('account.move', ondelete='cascade')      # Should be a One2one
    partner_id = fields.Many2one('res.partner', compute='_compute_partner_id')
    company_id = fields.Many2one('res.company', compute='_compute_company_id', recursive=True, store=True)
    can_send_response = fields.Boolean(compute='_compute_can_send_response')
    message_type = fields.Selection([
            ('invoice', 'Invoice'),
            ('response', 'Response'),
        ], compute='_compute_message_type',
    )

    @api.depends('response_ids.state', 'partner_id')
    def _compute_can_send_response(self):
        for message in self:
            message.can_send_response = (
                message.uuid
                and not message.origin_message_id
                and not message.response_ids.filtered(
                    lambda m: m.state == 'not_serviced' or (m.state != 'error' and m.response_code in ('AP', 'RE')),
                )
                and message.partner_id.peppol_response_support
            )

    @api.depends('move_id.partner_id')
    def _compute_partner_id(self):
        # No need to compute the partner for responses as the partner is used only on Main document to see if he supports responses.
        for message in self:
            message.partner_id = message.move_id.partner_id

    @api.depends('move_id.company_id', 'origin_message_id.company_id')
    def _compute_company_id(self):
        for message in self:
            if message.origin_message_id:
                message.company_id = message.origin_message_id.company_id
            else:
                message.company_id = message.move_id.company_id

    @api.depends('origin_message_id', 'response_ids.state')
    def _compute_response_code(self):
        for message in self:
            if not message.origin_message_id:
                response_types = message.response_ids.filtered(lambda m: m.state == 'done').mapped('response_code')
                message.response_code = (
                    'PD' if 'PD' in response_types else
                    'RE' if 'RE' in response_types else
                    'AP' if 'AP' in response_types else
                    'CA' if 'CA' in response_types else
                    'UQ' if 'UQ' in response_types else
                    'IP' if 'IP' in response_types else
                    'AB' if 'AB' in response_types else False
                )
            message.response_code = message.response_code

    @api.depends('origin_message_id')
    def _compute_message_type(self):
        for message in self:
            message.message_type = 'response' if message.origin_message_id else 'invoice'

    def action_peppol_send_approval_response(self):
        messages_to_respond_by_company = self.filtered('can_send_response').grouped('company_id')
        for company in messages_to_respond_by_company:
            company.account_peppol_edi_user._peppol_send_response(messages_to_respond_by_company[company], 'AP')

    def action_peppol_send_rejection_response(self):
        if default_reason := self.env.ref('account_peppol.peppol_clarification_reason_oth', raise_if_not_found=False):
            messages_to_respond_by_company = self.filtered('can_send_response').grouped('company_id')
            clarifications = [{
                'list_identifier': default_reason.list_identifier,
                'code': default_reason.code,
                'name': default_reason.name,
            }]
            for company in messages_to_respond_by_company:
                company.account_peppol_edi_user._peppol_send_response(
                    messages_to_respond_by_company[company],
                    'RE',
                    clarifications,
                )
            return {}
            # OR manually create a simple clarification
            # # Backup in case the peppol_clarification_reason_oth has been deleted somehow.
            # # Might be less up to date.
            # clarifications = [{
            #     'list_identifier': 'OPStatusReason',
            #     'code': 'OTH',
            #     'name': 'Reason for status is not defined by code.',
            # }]
        return self.action_peppol_open_rejection_wizard()

    def action_peppol_open_rejection_wizard(self):
        peppol_messages = self.filtered('can_send_response')
        if peppol_messages:
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Reject Peppol Document"),
                'view_mode': 'form',
                'res_model': 'account.peppol.rejection.wizard',
                'target': 'new',
                'res_id': self.env['account.peppol.rejection.wizard'].create({'message_ids': peppol_messages.ids}).id,
            }
        return {}

    def action_open_peppol_reponses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Peppol Responses"),
            'view_mode': 'list',
            'res_model': 'account.peppol.message',
            'domain': [('id', 'in', (self + self.response_ids).ids)],
        }

    def _log_message(self, message):
        response_messages = self.filtered('origin_message_id')
        moves = (self - response_messages | response_messages.origin_message_id).move_id
        if moves:
            if len(moves) > 1:
                moves._message_log_batch(bodies={move.id: message for move in moves})
            else:
                moves._message_log(body=message)
