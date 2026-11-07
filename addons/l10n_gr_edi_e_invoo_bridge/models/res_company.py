from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_gr_edi_methodoos_api_token = fields.Char(
        string='Methodoos API Token',
        groups='base.group_system',
        copy=False,
    )
