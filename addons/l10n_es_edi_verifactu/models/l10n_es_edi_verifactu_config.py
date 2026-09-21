from odoo import fields, models


class L10nEsEdiVerifactuConfig(models.Model):
    _name = "l10n_es_edi_verifactu.config"
    _description = "A company's l10n es edi verifactu configuration"
    _inherit = ["mixin.company.config"]

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Enable Veri*Factu",
        copy=False,
    )
    l10n_es_edi_verifactu_test_environment = fields.Boolean(
        string="Veri*Factu Test Environment",
        default=True,
        copy=False,
    )
    l10n_es_edi_verifactu_chain_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Veri*Factu Document Chain Sequence",
        copy=False,
        readonly=True,
    )
    l10n_es_edi_verifactu_next_batch_time = fields.Datetime(
        string="Veri*Factu Next Batch Time",
        copy=False,
        readonly=True,
        help="The Datetime at which the next submission to the AEAT can be made.",
    )
    l10n_es_edi_verifactu_special_vat_regime = fields.Selection(
        selection=[
            ("simplified", "Simplified Regime"),
            (
                "reagyp",
                "REAGYP (Special Regime for Agriculture, Livestock and Fisheries)",
            ),
            ("recargo", "Recargo de Equivalencia"),
        ],
        string="Veri*Factu VAT Regime",
        help="Leave empty for the normal regimen.",
    )
