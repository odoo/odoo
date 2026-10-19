from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_reports_tax_office_id = fields.Many2one('l10n_pl.l10n_pl_tax_office', string='Tax Office', groups="account.group_account_user")
