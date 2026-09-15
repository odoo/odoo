from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_fr_border_reference = fields.Many2one(comodel_name='l10n_fr.octroi.de.mer.code', string="Border reference")
    l10n_fr_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Rate",
        related='l10n_fr_border_reference.om_rate_id',
    )
    l10n_fr_regional_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Regional rate",
        related='l10n_fr_border_reference.omr_rate_id',
    )
