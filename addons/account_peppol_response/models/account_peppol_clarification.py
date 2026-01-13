from odoo import fields, models


class PeppolRejectionWizard(models.Model):
    _name = 'account.peppol.clarification'
    _description = "Peppol clarifications used for rejection"

    list_identifier = fields.Selection([
            ('OPStatusReason', 'OPStatusReason'),
            ('OPStatusAction', 'OPStatusAction'),
        ], string='List identifier',
    )
    code = fields.Char()
    name = fields.Char()
    description = fields.Char()
