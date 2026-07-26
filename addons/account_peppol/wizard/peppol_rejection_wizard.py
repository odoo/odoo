from odoo import fields, models
from odoo.exceptions import ValidationError


class PeppolRejectionWizard(models.TransientModel):
    _name = 'account.peppol.rejection.wizard'
    _description = "Peppol Rejection wizard"

    message_ids = fields.Many2many(
        comodel_name='account.peppol.message',
        required=True,
    )
    reason_ids = fields.Many2many(
        comodel_name='account.peppol.clarification',
        relation='account_peppol_rejection_reason_rel',
        default=lambda self: self.env.ref('account_peppol.peppol_clarification_reason_unr', raise_if_not_found=False),
        domain="[('list_identifier', '=', 'OPStatusReason')]",
        required=True,
        string='Rejection reasons',
        help="The reasons to reject the received PEPPOL document. "
        "These will be sent to the document's sender.",
    )
    action_ids = fields.Many2many(
        comodel_name='account.peppol.clarification',
        relation='account_peppol_rejection_action_rel',
        domain="[('list_identifier', '=', 'OPStatusAction')]",
        string='Rejection actions',
        help="The actions to be suggested to the document's sender in order for the document to be accepted when sent again (eventually). "
        "These will be sent to the document's sender. Not mandatory.",
    )

    def button_send(self):
        if not self.reason_ids:
            raise ValidationError(self.env._('At least one reason must be given when rejecting a Peppol document.'))
        clarifications = [{
            'list_identifier': clarification.list_identifier,
            'code': clarification.code,
            'name': clarification.name,
        } for clarification in self.reason_ids + self.action_ids]
        messages_by_company = self.message_ids.grouped('company_id')
        for company in messages_by_company:
            company.account_peppol_edi_user._peppol_send_response(messages_by_company[company], 'RE', clarifications)
        return self.env.context.get('cancel_res', True)
