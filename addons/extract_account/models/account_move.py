from __future__ import annotations

import logging

from odoo import api, fields, models
from odoo.exceptions import LockError, UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

CANDIDATE_LIMIT = 50


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "mixin.extract"]

    _extract_document_type = "invoice"

    _extract_target = {
        "invoice_date": "invoice_date",
        "invoice_number": "ref",
    }

    extract_can_be_read = fields.Boolean(compute="_compute_extract_can_be_read")
    extract_has_lines = fields.Boolean(compute="_compute_extract_has_lines")
    extract_lines_applied = fields.Boolean(
        copy=False,
        readonly=True,
        help="Whether the lines read from the document have already been added "
        "to this bill. Kept so the screen that offers them cannot add them "
        "a second time.",
    )

    @api.depends("state", "move_type", "extract_state")
    def _compute_extract_can_be_read(self) -> None:
        for move in self:
            move.extract_can_be_read = (
                move.state == "draft"
                and move.is_purchase_document()
                and move.extract_state in ("none", "failed", "partial")
            )

    @api.depends("extract_result", "state", "extract_lines_applied")
    def _compute_extract_has_lines(self) -> None:
        for move in self:
            read = move._extract_read_lines()
            move.extract_has_lines = (
                bool(read.get("value"))
                and move.state == "draft"
                and not move.extract_lines_applied
            )

    def _extract_read_lines(self) -> dict:
        return (self.extract_result or {}).get("lines") or {}

    def _get_extract_document_type(self) -> str:
        self.check_singleton()
        return self._extract_document_type if self.is_purchase_document() else ""

    def _update_from_extraction(self, result) -> None:
        self.check_singleton()
        super()._update_from_extraction(result)

        values = result.flat()
        writes = {}

        if not self.partner_id:
            partner = self._get_extract_partner(values.get("vendor_vat"))
            if partner:
                writes["partner_id"] = partner.id

        currency = self._get_extract_currency(values.get("currency"))
        if (
            currency
            and currency != self.currency_id
            and self._extract_may_set_currency()
        ):
            writes["currency_id"] = currency.id

        if self.extract_lines_applied:
            writes["extract_lines_applied"] = False

        if writes:
            self.write(writes)

        if values.get("due_date") and not self.invoice_payment_term_id:
            self.invoice_date_due = values["due_date"]

        lines = values.get("lines")
        if lines:
            _logger.info(
                "Read %d line(s) from the document on %s; they are recorded in "
                "extract_result and not posted, because a line decides an "
                "account and a tax",
                len(lines),
                self.name or self.id,
            )

    def _get_extract_partner(self, vat: str | None):
        if not vat:
            return None
        candidates = self.env["res.partner"].search(
            [
                ("vat", "=ilike", vat.strip()),
                ("company_id", "in", (False, self.company_id.id)),
            ],
            limit=CANDIDATE_LIMIT,
        )
        if len(candidates) == CANDIDATE_LIMIT:
            _logger.info(
                "More than %s partners carry the tax identifier %r; none chosen",
                CANDIDATE_LIMIT,
                vat,
            )
            return None

        companies = candidates.commercial_partner_id
        if len(companies) != 1:
            if companies:
                _logger.info(
                    "%s distinct partners share the tax identifier %r; none chosen",
                    len(companies),
                    vat,
                )
            return None
        return companies

    def _extract_may_set_currency(self) -> bool:
        self.check_singleton()
        default = self.journal_id.currency_id or self.company_id.currency_id
        return self.currency_id == default and not self.invoice_line_ids

    def _get_extract_currency(self, name: str | None):
        if not name:
            return None
        return self.env["res.currency"].search(
            [("name", "=", name.strip().upper())], limit=1
        )

    @api.model
    def _extract_line_seed(self, line: dict) -> dict:
        # `invoice.lines` declares a row and requires its description, so a line
        # with nothing to call it never arrives and no name has to be invented
        # for it. Quantity and price are optional and keep their defaults.
        quantity = line.get("quantity")
        price = line.get("unit_price")
        return {
            "description": line["description"],
            "quantity": 1.0 if quantity is None else quantity,
            "price_unit": 0.0 if price is None else price,
        }

    @api.model
    def _extract_line_differs(self, proposal, seed: dict) -> bool:
        currency = proposal.currency_id or self.currency_id
        if currency.compare_amounts(proposal.price_unit, seed["price_unit"]):
            return True
        digits = proposal._fields["quantity"].get_digits(self.env)
        precision = digits[1] if digits else 2
        if float_compare(
            proposal.quantity, seed["quantity"], precision_digits=precision
        ):
            return True
        return proposal.description != seed["description"]

    def action_review_extracted_lines(self):
        self.check_singleton()
        if self.state != "draft":
            raise UserError(
                self.env._("Only a draft bill can take lines read from its document.")
            )
        lines = self._extract_read_lines().get("value") or []
        if not lines:
            raise UserError(self.env._("No lines were read from this bill's document."))

        wizard = self.env["account.move.extract.line.wizard"].create(
            self.env["account.move.extract.line.wizard"]._prepare_from_move(self)
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Lines read from the document"),
            "res_model": "account.move.extract.line.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _add_extraction_correction_for_lines(self, proposals) -> None:
        self.check_singleton()
        read = self._extract_read_lines().get("value") or []
        changed = []
        for proposal in proposals:
            if not 0 <= proposal.read_index < len(read):
                continue
            original = read[proposal.read_index]
            if not proposal.accepted:
                changed.append({"read": original, "corrected_to": None})
                continue
            if self._extract_line_differs(proposal, self._extract_line_seed(original)):
                changed.append(
                    {
                        "read": original,
                        "corrected_to": {
                            "description": proposal.description,
                            "quantity": proposal.quantity,
                            "unit_price": proposal.price_unit,
                        },
                    }
                )
        if not changed:
            return
        source = self._extract_read_lines().get("source")
        stored = dict(self.extract_corrections or {})
        previous = (stored.get("lines") or {}).get("changes") or []
        stored["lines"] = {
            "read_by": source,
            "changes": [*previous, *({**c, "read_by": source} for c in changed)],
        }
        self.with_context(extracting=True).write({"extract_corrections": stored})

    def action_extract_document(self):
        self.check_singleton()
        if not self._get_extract_document_type():
            raise UserError(
                self.env._(
                    "Only a vendor bill carries a document this can read. "
                    "%(name)s is not one.",
                    name=self.display_name,
                )
            )
        try:
            self.lock_for_update()
        except LockError as error:
            raise UserError(
                self.env._(
                    "This bill's document is already being read. Try again in a moment."
                )
            ) from error
        result = self._extract_document()
        if result is None:
            return False
        if result.satisfied:
            message = self.env._("The document was read in full.")
        else:
            message = self.env._(
                "The document was read in part. Still missing: %(fields)s",
                fields=", ".join(result.missing) or self.env._("nothing required"),
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "info", "sticky": False},
        }
