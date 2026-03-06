from odoo import fields, models


class GovNlEventoExt(models.Model):
    """
    Extensao de gov.nl.evento para adicionar pd_id sem acoplamento reverso.
    """

    _inherit = "gov.nl.evento"

    pd_id = fields.Many2one(
        "gov.pd",
        string="PD Vinculada",
        readonly=True,
        copy=False,
        index=True,
        ondelete="set null",
        help="Programacao de Desembolso que consumiu este evento.",
    )
