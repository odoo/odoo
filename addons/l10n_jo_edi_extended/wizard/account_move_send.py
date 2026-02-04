from odoo import fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_jo_edi_demo_mode = fields.Boolean(related='company_id.l10n_jo_edi_demo_mode')
