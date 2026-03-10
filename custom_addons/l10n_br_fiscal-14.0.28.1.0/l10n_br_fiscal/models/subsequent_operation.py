# Copyright (C) 2020  KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import fields, models

from ..constants.fiscal import SITUACAO_EDOC

SUBSEQUENT_CONDITION = [
    ("manual", "Manualmente"),
    ("nota_de_cupom", "Gerar Nota Fiscal de Cupons Fiscais"),
    ("nota_de_remessa", "Gerar Nota Fiscal de Remessa"),
]

SUBSEQUENT_OPERATION = SITUACAO_EDOC + SUBSEQUENT_CONDITION


class SubsequentOperation(models.Model):
    """We must be aware that some subsequent operations do not generate
    financial moves"""

    _name = "l10n_br_fiscal.subsequent.operation"
    _description = "Subsequent Operation"
    _rec_name = "fiscal_operation_id"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        help="Gives the sequence order when displaying a list",
    )
    fiscal_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        string="Origin operation",
        required=True,
        ondelete="cascade",
    )
    subsequent_operation_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.operation",
        string="Operation to be performed",
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    generation_situation = fields.Selection(
        selection=SUBSEQUENT_OPERATION,
        required=True,
        default="manual",
    )
    reference_document = fields.Boolean(
        string="Referencing source document",
    )

    operation_document_type_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.type",
        string="Document Type",
    )
