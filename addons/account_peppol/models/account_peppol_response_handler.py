from odoo import api, fields, models

RESPONSE_STATES = [
    ('AB', 'Received'),
    ('AP', 'Approved'),
    ('RE', 'Rejected'),
]


class AccountPeppolResponseHandlerRel(models.Model):
    _name = 'account.peppol.response.handler.rel'

    response_ids = fields.One2many('account.peppol.response')
    move_id = fields.Many2one('account_move')

    def _get_handler_record(self):
        


class AccountPeppolResponseHandler(models.AbstractModel):
    _name = 'account.peppol.response.handler'
    _description = "Handler to be use on any records that needs to handle responses from Peppol."
    _partner_fname = 'partner_id'

    peppol_message_uuid = fields.Char(string='Peppol message ID', copy=False)
    peppol_response_state = fields.Selection(
        selection=RESPONSE_STATES,
        string='Peppol status',
        copy=False,
    )
    peppol_response_ids = fields.One2many('account.peppol.response', 'handler_id')
    peppol_can_send_response = fields.Boolean(compute='_compute_peppol_can_send_response')
    company_id = fields.Many2one('res.company')

    @api.depends("peppol_response_ids.peppol_state")
    def _compute_peppol_can_send_response(self):
        for handler in self:
            handler.peppol_can_send_response = (
                handler.peppol_message_uuid
                and not handler.peppol_response_ids.filtered(
                    lambda r: r.peppol_state == 'not_serviced' or (r.peppol_state != 'error' and r.response_code in ('AP', 'RE')),
                )
                and handler[handler._partner_fname].peppol_response_support
            )

    @api.depends('peppol_response_ids.peppol_state')
    def _compute_peppol_response_state(self):
        for handler in self:
            if valid_statuses := handler.peppol_response_ids.filtered(lambda r: r.peppol_state == 'done').mapped('response_code'):
                if 'RE' in valid_statuses:
                    handler.peppol_response_state = 'RE'
                elif any(status in {'AP', 'PD'} for status in valid_statuses):
                    handler.peppol_response_state = 'AP'
                else:
                    handler.peppol_response_state = 'AB'
            else:
                handler.peppol_response_state = False

    def action_peppol_send_approval_response(self):
        handlers_to_respond_by_company = self.filtered('peppol_can_send_response').grouped(self._company_fname)
        for company in handlers_to_respond_by_company:
            company.account_peppol_edi_user._peppol_send_response(handlers_to_respond_by_company[company], 'AP')

    def action_peppol_send_rejection_response(self):
        if default_reason := self.env.ref('account_peppol.peppol_clarification_reason_oth', raise_if_not_found=False):
            handlers_to_respond_by_company = self.filtered('peppol_can_send_response').grouped(self._company_fname)
            clarifications = [{
                'list_identifier': default_reason.list_identifier,
                'code': default_reason.code,
                'name': default_reason.name,
            }]
            for company in handlers_to_respond_by_company:
                company.account_peppol_edi_user._peppol_send_response(
                    handlers_to_respond_by_company[company],
                    'RE',
                    clarifications,
                )
            return {}
            # OR create a simple clarification
            # # Backup in case the peppol_clarification_reason_oth has been deleted somehow.
            # # Might be less up to date.
            # clarifications = [{
            #     'list_identifier': 'OPStatusReason',
            #     'code': 'OTH',
            #     'name': 'Reason for status is not defined by code.',
            # }]
        return self.action_peppol_open_rejection_wizard()

    def action_peppol_open_rejection_wizard(self):
        peppol_handlers = self.filtered('peppol_can_send_response')
        if peppol_handlers:
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Reject Peppol Document"),
                'view_mode': 'form',
                'res_model': 'account.peppol.rejection.wizard',
                'target': 'new',
                'res_id': self.env['account.peppol.rejection.wizard'].create({'handler_ids': peppol_handlers.ids}).id,
            }
        return {}

    def action_open_peppol_reponses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Peppol Responses"),
            'view_mode': 'list',
            'res_model': 'account.peppol.response',
            'domain': [('id', 'in', self.peppol_response_ids.ids)],
        }
