from odoo import models, fields


class TaxGroups(models.Model):
    _inherit = 'account.tax.group'

    l10n_hr_fiscalization_tax_group_id = fields.Selection([
        ('pdv', 'PDV'),
        ('pnp', 'PNP'),
        ('other_taxes', 'Ostali porezi')
    ], string='Tax Group', default='pdv')
