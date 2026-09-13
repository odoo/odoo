from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import UserError


def _read_untaxed_total(result: dict) -> float:
    subtotal = (result.get("subtotal") or {}).get("value")
    if subtotal is not None:
        return subtotal
    total = (result.get("total") or {}).get("value") or 0.0
    tax = (result.get("tax_amount") or {}).get("value")
    return total - tax if tax is not None else total


class ExtractLineProposal(models.TransientModel):
    _name = "account.move.extract.line.proposal"
    _description = "Line Read From a Document, Awaiting a Person"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="account.move.extract.line.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    read_index = fields.Integer(
        readonly=True,
        help="Position of this line in what the document said. Kept so a "
        "correction is attributed to the line it was made on even after the "
        "rows are reordered.",
    )
    accepted = fields.Boolean(default=True)
    description = fields.Char(required=True)
    quantity = fields.Float(default=1.0)
    price_unit = fields.Monetary(currency_field="currency_id")
    product_id = fields.Many2one(comodel_name="product.product")
    read_by = fields.Char(readonly=True)
    confidence = fields.Float(
        digits=(3, 2),
        readonly=True,
    )
    currency_id = fields.Many2one(related="wizard_id.move_id.currency_id")
    subtotal = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_subtotal",
    )

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self) -> None:
        for proposal in self:
            proposal.subtotal = proposal.quantity * proposal.price_unit


class ExtractLineWizard(models.TransientModel):
    _name = "account.move.extract.line.wizard"
    _description = "Review Lines Read From a Document"

    move_id = fields.Many2one(
        comodel_name="account.move",
        readonly=True,
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="account.move.extract.line.proposal",
        inverse_name="wizard_id",
    )
    currency_id = fields.Many2one(related="move_id.currency_id")
    read_total = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    read_untaxed_total = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    proposed_total = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_proposed_total",
    )
    totals_agree = fields.Boolean(compute="_compute_totals_agree")

    @api.depends("line_ids.subtotal", "line_ids.accepted")
    def _compute_proposed_total(self) -> None:
        for wizard in self:
            wizard.proposed_total = sum(
                line.subtotal for line in wizard.line_ids if line.accepted
            )

    @api.depends("proposed_total", "read_untaxed_total", "currency_id")
    def _compute_totals_agree(self) -> None:
        for wizard in self:
            currency = wizard.currency_id or wizard.move_id.company_id.currency_id
            wizard.totals_agree = (
                currency.compare_amounts(
                    wizard.proposed_total, wizard.read_untaxed_total
                )
                == 0
                if wizard.read_untaxed_total
                else True
            )

    @api.model
    def _prepare_from_move(self, move) -> dict:
        result = move.extract_result or {}
        envelope = move._extract_read_lines()
        lines = envelope.get("value") or []
        return {
            "move_id": move.id,
            "read_total": (result.get("total") or {}).get("value") or 0.0,
            "read_untaxed_total": _read_untaxed_total(result),
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "sequence": index * 10,
                        "read_index": index,
                        "read_by": envelope.get("source") or "",
                        "confidence": envelope.get("confidence") or 0.0,
                        **move._extract_line_seed(line),
                    },
                )
                for index, line in enumerate(lines)
            ],
        }

    def action_apply(self):
        self.check_singleton()
        move = self.move_id
        if move.state != "draft":
            raise UserError(
                self.env._("Only a draft bill can take lines read from its document.")
            )
        if move.extract_lines_applied:
            raise UserError(
                self.env._(
                    "The lines read from this document were already added to "
                    "this bill. Read the document again to offer them afresh."
                )
            )

        accepted = self.line_ids.filtered("accepted")
        if not accepted:
            raise UserError(self.env._("No line was accepted, so nothing was added."))

        move.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": line.description,
                            "quantity": line.quantity,
                            "price_unit": line.price_unit,
                            **(
                                {"product_id": line.product_id.id}
                                if line.product_id
                                else {}
                            ),
                        },
                    )
                    for line in accepted
                ]
            }
        )
        move._add_extraction_correction_for_lines(self.line_ids)
        move.extract_lines_applied = True
        return {"type": "ir.actions.act_window_close"}
