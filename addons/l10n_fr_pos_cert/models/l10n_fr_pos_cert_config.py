from odoo import fields, models


class L10nFrPosCertConfig(models.Model):
    _name = "l10n_fr_pos_cert.config"
    _description = "A company's l10n fr pos cert configuration"
    _inherit = ["mixin.company.config"]

    l10n_fr_pos_cert_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Sequence to secure point of sale orders",
        readonly=True,
    )
