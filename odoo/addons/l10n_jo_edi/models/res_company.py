from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jo_edi_sequence_income_source = fields.Char(string="Sequence of Income Source")
    l10n_jo_edi_secret_key = fields.Char(string="Jordan EINV Secret Key", groups="base.group_system")
    l10n_jo_edi_client_identifier = fields.Char(string="Jordan EINV Client ID", groups="base.group_system")
    l10n_jo_edi_taxpayer_type = fields.Selection(string="Taxpayer type", selection=[
        ('income', "Unregistered in the sales tax"),
        ('sales', "Registered in the sales tax"),
        ('special', "Registered in the special sales tax"),
    ])
