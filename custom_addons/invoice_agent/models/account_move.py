import base64
import io
import json
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .llm_service import AIServiceUnavailable

_logger = logging.getLogger(__name__)

_CLAUDE_SYSTEM_PROMPT = (
    'object like: {"company_name": "...", "vat": "...", "amount_total": 0, '
    '"overall_confidence": 0.0, "invoice_date": "YYYY-MM-DD", '
    '"invoice_date_due": "YYYY-MM-DD", "ref": "...", "lines": '
    '[{"name": "...", "quantity": 1, "price_unit": 0, "confidence": 0.0}], '
    '"notes": "...", "review_required": false}. Never wrap it in markdown.'
)


class AccountMove(models.Model):
    _inherit = "account.move"

    # === AI Extraction Fields ===
    ai_source_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="AI Source Attachment",
        ondelete="set null",
        help="The source PDF or image attachment that was processed by the AI extraction service.",
    )
    ai_ocr_text = fields.Text(
        string="AI OCR Text",
        help="Raw OCR text extracted from the source PDF/image by the AI service.",
    )
    ai_model_used = fields.Char(
        string="AI Model Used",
        help="Identifier of the AI model used for extraction.",
    )
    ai_review_required = fields.Boolean(
        string="AI Review Required",
        tracking=True,
        default=False,
        help="When checked, this document's AI extraction needs human review before posting.",
    )
    ai_extraction_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("extracted", "Extracted"),
            ("validated", "Validated"),
            ("failed", "Failed"),
        ],
        string="AI Extraction Status",
        default="pending",
        index=True,
        tracking=True,
        help="Current state of AI data extraction for this document.",
    )
    ai_confidence = fields.Float(
        string="AI Overall Confidence",
        digits=(3, 2),
        tracking=True,
        help="Overall extraction confidence score between 0.00 and 1.00.",
    )
    # === Week-7 Confidence Routing (calibrated, never the raw self-report) ===
    confidence_score = fields.Float(
        string="Confidence Score",
        compute="_compute_confidence_score",
        store=True,
        digits=(3, 2),
        readonly=True,
        index=True,
        help="Calibrated blend of the model's self-reported certainty, the "
        "Tesseract per-word confidence, and the deterministic cross-checks "
        "(arithmetic line-sum, VAT/IBAN regex rescue). This is the score the "
        "routing threshold compares against — the self-reported "
        "field_confidence is only one input, weighted and audited.",
    )
    ai_confidence_details = fields.Json(
        string="Confidence Details",
        compute="_compute_confidence_score",
        store=True,
        readonly=True,
        help="Audit trail for confidence_score: every input, the blend "
        "weights, the verified cross-check list, and which fallback path "
        "fired on this move (normal pass, high-effort pass, rescue:vat, "
        "rescue:iban, arithmetic).",
    )
    ai_confidence_notes = fields.Text(
        string="Confidence Notes",
        compute="_compute_confidence_score",
        store=True,
        readonly=True,
        help="Free-text ambiguity notes from the extraction (schema 'notes'), "
        "surfaced verbatim on the Needs Review chatter message.",
    )
    ai_extraction_state = fields.Selection(
        selection=[
            ("auto", "Auto"),
            ("needs_review", "Needs Review"),
            ("approved", "Approved"),
        ],
        string="Extraction State",
        compute="_compute_confidence_score",
        store=True,
        readonly=True,
        index=True,
        help="Kanban routing state: 'auto' when confidence cleared the "
        "journal threshold, 'needs_review' when it did not (or the pipeline "
        "failed), 'approved' when a human validated the bill.",
    )
    ai_extracted_json = fields.Json(
        string="AI Extracted Raw Payload",
        help="JSON blob containing full unprocessed OCR/AI response.",
    )
    # === Persisted raw Structured-Output payload (Suggest with AI) ===
    extraction_json = fields.Text(
        string="Extraction JSON",
        readonly=True,
        help="Raw schema-validated payload returned by the Claude extraction "
        "service (client.messages.parse). Persisted verbatim so later prompt "
        "changes stay auditable against real output.",
    )
    extraction_model = fields.Char(
        string="Extraction Model",
        readonly=True,
        help="Anthropic model id that produced extraction_json "
        "(e.g. claude-opus-4-8).",
    )
    ai_error_message = fields.Text(
        string="AI Error Message",
        readonly=True,
        help="Last error raised by the extraction pipeline, when ai_extraction_status is 'failed'.",
    )
    ai_extracted_on = fields.Datetime(
        string="AI Extracted On",
        readonly=True,
        help="Timestamp when data extraction completed.",
    )
    ai_validated_on = fields.Datetime(
        string="AI Validated On",
        readonly=True,
        help="Timestamp when data validation completed.",
    )
    extraction_line_ids = fields.One2many(
        comodel_name="invoice.agent.extraction.line",
        inverse_name="move_id",
        string="Per-Field Extraction Data",
    )

    # === AI Extracted Total ===
    ai_extracted_total = fields.Monetary(
        string="AI Extracted Total",
        readonly=True,
        help="Total amount extracted from the source document by the AI service.",
    )

    # === Variance ===
    ai_amount_variance = fields.Monetary(
        string="AI Amount Variance",
        compute="_compute_ai_variance",
        store=True,
        readonly=True,
        help="Difference between AI-extracted total and the system-computed total.",
    )
    ai_variance_pct = fields.Float(
        string="AI Variance %",
        compute="_compute_ai_variance",
        store=True,
        digits=(5, 4),
        readonly=True,
        help="Relative variance as a percentage of the system total.",
    )
    ai_needs_review = fields.Boolean(
        string="AI Needs Review",
        compute="_compute_ai_variance",
        store=True,
        readonly=True,
        help="Flagged when variance exceeds the journal's configured threshold.",
    )

    # === Average confidence across all invoice lines ===
    ai_line_confidence_avg = fields.Float(
        string="Line Confidence Avg",
        compute="_compute_ai_line_confidence_avg",
        store=True,
        digits=(3, 2),
        readonly=True,
        help="Average AI confidence across all invoice lines.",
    )

    # === Link to originating sale order ===
    ai_source_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Source Sale Order",
        ondelete="set null",
        index=True,
        copy=False,
        help="The sale order that generated this invoice, when known from AI extraction.",
    )

    # === OCR Pipeline Fields (see docs/adr-002-ocr-engine.md) ===
    # ``ocr_state`` is the OCR half of the extraction state machine, separate
    # from ``ai_extraction_status`` because the two run on different
    # cadences: OCR runs once on the raw attachment (seconds, via ir.cron),
    # while the Claude extraction can be re-run interactively on the stored
    # text. State transitions: pending -> running -> done | failed.
    ocr_state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        string="OCR State",
        default="pending",
        index=True,
        tracking=True,
        help="State of the Tesseract OCR job for the source attachment. "
        "pending: queued for the cron; running: claimed by a cron worker; "
        "done: text + confidence stored; failed: nothing stored.",
    )
    ocr_text = fields.Text(
        string="OCR Text",
        readonly=True,
        help="Raw text extracted from the source attachment by Tesseract. "
        "Empty until ocr_state is 'done'.",
    )
    ocr_confidence = fields.Float(
        string="OCR Confidence",
        digits=(3, 2),
        readonly=True,
        help="Mean per-word confidence from Tesseract's image_to_data, 0..1.",
    )
    ocr_engine = fields.Char(
        string="OCR Engine",
        readonly=True,
        default="tesseract",
        help="OCR engine that produced ocr_text (always 'tesseract' today; "
        "the Textract fallback is documented in ADR-002 but not wired).",
    )
    ocr_error_message = fields.Text(
        string="OCR Error Message",
        readonly=True,
        help="Last OCR failure reason when ocr_state is 'failed'.",
    )

    # -------------------------------------------------------------------------
    # COMPUTE: AI Variance
    # -------------------------------------------------------------------------
    @api.depends("amount_total", "ai_extracted_total", "currency_id")
    def _compute_ai_variance(self):
        for move in self:
            total = move.amount_total or 0.0
            ai_total = move.ai_extracted_total or 0.0
            move.ai_amount_variance = ai_total - total
            if total:
                move.ai_variance_pct = (ai_total - total) / total
            else:
                move.ai_variance_pct = 0.0
            threshold = (
                move.journal_id.ai_min_confidence
                if move.journal_id.ai_agent_enabled
                else 0.05
            )
            move.ai_needs_review = abs(move.ai_variance_pct) > threshold

    # -------------------------------------------------------------------------
    # COMPUTE: Average line confidence
    # -------------------------------------------------------------------------
    @api.depends("invoice_line_ids.ai_confidence")
    def _compute_ai_line_confidence_avg(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(
                lambda line: line.ai_confidence is not None,
            )
            if lines:
                move.ai_line_confidence_avg = sum(lines.mapped("ai_confidence")) / len(
                    lines,
                )
            else:
                move.ai_line_confidence_avg = 0.0

    # -------------------------------------------------------------------------
    # COMPUTE: Confidence score + kanban routing state (week 7)
    # -------------------------------------------------------------------------
    # The stored ``confidence_score`` is the calibrated blend computed by
    # ``invoice.llm.service.score_extraction`` (self-report + OCR conf +
    # arithmetic + VAT/IBAN rescue), over the persisted ``ai_extracted_json``
    # payload. When no payload has been scored yet the score is 0 and the
    # routing state is ``needs_review`` — an unscored bill must never slip
    # through as Auto.
    #
    # Routing:
    #   * ``approved``  — human validated the bill.
    #   * ``auto``      — scored >= journal threshold (``ai_min_confidence``).
    #   * ``needs_review`` — scored below threshold, pipeline failed, or no
    #     payload at all.
    # -------------------------------------------------------------------------
    @api.depends(
        "ai_extracted_json",
        "ai_extraction_status",
        "ai_review_required",
        "ai_confidence",
        "ocr_confidence",
        "ocr_text",
        "journal_id.ai_agent_enabled",
        "journal_id.ai_min_confidence",
    )
    def _compute_confidence_score(self):
        for move in self:
            move._score_and_route_move()

    def _score_and_route_move(self):
        """Score one move and set its kanban routing state.

        Never raises: a malformed stored payload or a missing OCR text
        degrades the move to ``needs_review`` so nothing silently slips
        through as Auto.
        """
        self.ensure_one()
        payload = self.ai_extracted_json
        if not isinstance(payload, dict):
            payload = {}

        if self.ai_extraction_status == "validated":
            # A human confirmed the bill — the state is Approved regardless
            # of the (already constraint-checked) threshold.
            self.confidence_score = self.ai_confidence or 0.0
            self.ai_confidence_details = self.ai_confidence_details or {}
            self.ai_confidence_notes = self.ai_confidence_notes or ""
            self.ai_extraction_state = "approved"
            return

        if not payload or self.ai_review_required:
            # Unscored (pending/processing), flagged by a human, or an empty
            # payload — never Auto.
            self.confidence_score = self.confidence_score or 0.0
            self.ai_confidence_details = self.ai_confidence_details or {}
            self.ai_confidence_notes = self.ai_confidence_notes or ""
            self.ai_extraction_state = "needs_review"
            return

        checks = []
        if self.ai_confidence_details and isinstance(self.ai_confidence_details, dict):
            checks = list(self.ai_confidence_details.get("checks") or [])

        score, details = self.env["invoice.llm.service"].score_extraction(
            payload,
            ocr_text=self.ocr_text or self.ai_ocr_text,
            ocr_confidence=self.ocr_confidence,
            checks=checks,
        )

        notes = payload["notes"] if isinstance(payload.get("notes"), str) else ""

        # Re-rescue the (possibly mutated) payload so the audit trail and the
        # stored payload stay in sync with what the blend actually saw.
        if details.get("checks") and self.ai_extracted_json != payload:
            self.ai_extracted_json = payload

        self.confidence_score = score
        self.ai_confidence_details = details
        self.ai_confidence_notes = notes

        threshold = self._get_ai_min_confidence()
        if self.ai_extraction_status == "failed":
            self.ai_extraction_state = "needs_review"
        elif score >= threshold:
            self.ai_extraction_state = "auto"
        else:
            self.ai_extraction_state = "needs_review"
            self.ai_review_required = True

    def _flag_needs_review(self, reason="low confidence"):
        """Mark a bill for human review and post the reason on the chatter.

        Called by the routing helpers whenever a move must not quietly
        produce an untouched draft: sub-threshold score, failed pipeline, or
        an explicit review flag. Setting ``ai_review_required`` drives the
        routing compute to ``needs_review``; ``message_post`` makes the
        reason visible on the bill's chatter so the accountant sees it in
        the queue too.
        """
        self.ensure_one()
        self.write({"ai_review_required": True})
        body = (
            "\u26a0\ufe0f <b>AI Needs Review</b><br/>"
            "Confidence score: <b>%.0f%%</b><br/>Reason: %s"
        ) % ((self.confidence_score or 0.0) * 100, reason)
        if self.ai_confidence_notes:
            body += "<br/>Notes: <i>%s</i>" % self.ai_confidence_notes
        try:
            self.message_post(
                body=body,
                subject="AI Needs Review: %s" % self.display_name,
            )
        except Exception:
            _logger.exception(
                "invoice_agent failed to post review message on %s",
                self.display_name,
            )

    @api.constrains("ai_confidence", "ai_extraction_status")
    def _check_ai_confidence_validation(self):
        for move in self:
            if (
                move.ai_extraction_status == "validated"
                and move.ai_confidence is not None
                and move.ai_confidence < self._get_ai_min_confidence()
            ):
                raise ValidationError(
                    _(
                        "AI extraction cannot be validated with confidence %.0f%% — "
                        "minimum %.0f%% required for journal '%s'.",
                        move.ai_confidence * 100,
                        self._get_ai_min_confidence() * 100,
                        move.journal_id.display_name,
                    ),
                )

    def _get_ai_min_confidence(self):
        """Resolve the routing threshold for this move.

        Priority: the global ``invoice_agent.confidence_threshold``
        ir.config_parameter (zero-downtime tuning / rollback, see
        ``invoice.llm.service.confidence_threshold``) → the journal's
        ``ai_min_confidence`` → 0.70 default.
        """
        self.ensure_one()
        global_threshold = self.env["invoice.llm.service"].confidence_threshold()
        if global_threshold is not None:
            return global_threshold
        if self.journal_id.ai_agent_enabled:
            return self.journal_id.ai_min_confidence
        return 0.70

    # -------------------------------------------------------------------------
    # SUGGEST WITH AI (Structured Outputs)
    # -------------------------------------------------------------------------
    # The header button "Suggest with AI" calls :meth:`action_suggest_extraction`
    # which runs the schema-validated pipeline (``invoice.llm.service.
    # extract_invoice`` -> ``client.messages.parse(output_format=
    # InvoiceExtraction)``), persists the raw payload into ``extraction_json``
    # + ``extraction_model`` (auditability), seeds one ``extraction_line`` per
    # suggested field, and returns a client notification to the browser. The
    # OWL suggestion panel then lets the accountant accept/reject one value at
    # a time; each accept hits :meth:`apply_suggested_value`, which re-reads
    # the value from the persisted payload (never from client input) and
    # applies exactly one field.
    # -------------------------------------------------------------------------
    def _suggested_vendor_id(self, extraction):
        """Best-effort partner resolution for the suggested vendor_name."""
        self.ensure_one()
        partner = self.env["res.partner"]
        if extraction.vendor_vat:
            partner = partner.search(
                [("vat", "=", extraction.vendor_vat), ("parent_id", "=", False)],
                limit=1,
            )
        if not partner and extraction.vendor_name:
            partner = partner.search(
                [("name", "ilike", extraction.vendor_name), ("parent_id", "=", False)],
                limit=1,
            )
        return partner.id or False

    def _suggested_field_lines(self, payload):
        """Turn a JSON-safe extraction payload into per-field suggestion rows.

        ``payload`` is the serialized dict from ``invoice.llm.service.
        extraction_to_dict`` (strings for dates, floats for Decimals) — never
        the raw pydantic model, whose model_dump() output contains Decimal /
        date objects that ``json.dumps`` cannot encode.

        Every row stores ``field_name``, ``extracted_value`` (raw, for the
        panel) and ``field_confidence``. The OWL chips render one row each.
        """
        self.ensure_one()
        currency_code = payload.get("currency") or ""
        currency = (
            self.env["res.currency"].search([("name", "=", currency_code)], limit=1)
            if currency_code
            else self.env["res.currency"]
        )
        # Per-field self-reported confidence from the schema's
        # ``field_confidence`` block, when the model provided it. The OWL
        # panel renders the chip with this number instead of a flat 1.0.
        reported = payload.get("field_confidence") or {}
        if not isinstance(reported, dict):
            reported = {}

        def _field_conf(key):
            value = reported.get(key)
            try:
                return float(value) if value is not None else 1.0
            except (TypeError, ValueError):
                return 1.0

        suggested = [
            {
                "field_name": "vendor_name",
                "extracted_value": payload.get("vendor_name") or "",
                "field_confidence": _field_conf("vendor_name"),
            },
            {
                "field_name": "vendor_vat",
                "extracted_value": payload.get("vendor_vat") or "",
                "field_confidence": _field_conf("vendor_vat"),
            },
            {
                "field_name": "invoice_date",
                "extracted_value": payload.get("invoice_date") or "",
                "field_confidence": _field_conf("invoice_date"),
            },
            {
                "field_name": "due_date",
                "extracted_value": payload.get("due_date") or "",
                "field_confidence": _field_conf("due_date"),
            },
            {
                "field_name": "currency",
                "extracted_value": currency_code,
                "field_confidence": _field_conf("currency"),
            },
            {
                "field_name": "subtotal",
                "extracted_value": payload.get("subtotal"),
                "field_confidence": _field_conf("subtotal"),
            },
            {
                "field_name": "tax_total",
                "extracted_value": payload.get("tax_total"),
                "field_confidence": _field_conf("tax_total"),
            },
            {
                "field_name": "amount_total",
                "extracted_value": payload.get("amount_total"),
                "field_confidence": _field_conf("amount_total"),
            },
        ]
        for index, line in enumerate(payload.get("lines") or []):
            line_conf = 1.0
            if isinstance(line, dict) and line.get("confidence") is not None:
                try:
                    line_conf = float(line["confidence"])
                except (TypeError, ValueError):
                    line_conf = 1.0
            suggested.append(
                {
                    "field_name": f"line:{index}",
                    "extracted_value": json.dumps(line),
                    "field_confidence": line_conf,
                },
            )
        return suggested

    def action_suggest_extraction(self):
        """Header-button handler: run Claude extraction on this draft bill.

        Guards:
        * record must be a draft vendor bill (UI also hides the button)
        * ``ai_extraction_status == 'processing'`` blocks a double
          submission — a second click while a call is in flight raises.

        On success: persists ``extraction_json`` + ``extraction_model`` (raw
        schema-validated payload — the audit trail), writes the suggested
        vendor/date values that are safe to auto-apply, seeds per-field
        ``extraction_line_ids`` for Accept/Reject, and returns a client
        notification. On failure: degrades to ``failed`` and notifies instead
        of raising into the UI.
        """
        self.ensure_one()
        if self.ai_extraction_status == "processing":
            raise UserError(_("An extraction is already running on this bill."))
        if self.state != "draft":
            raise UserError(_("Suggest with AI only works on draft bills."))

        self.write(
            {
                "ai_extraction_status": "processing",
                "ai_error_message": False,
            },
        )
        try:
            ocr_text = self.ai_ocr_text or self._invoice_agent_ocr()
            result = self.env["invoice.llm.service"].extract_invoice(ocr_text)
            extraction = result["parsed"]
            payload = self.env["invoice.llm.service"].extraction_to_dict(
                extraction,
            )
            summary = (
                f"{extraction.vendor_name} — {extraction.invoice_date} — "
                f"{extraction.amount_total} {extraction.currency}"
            )

            # Auto-apply the values that are safe (vendor match + dates) and
            # keep the rest as Accept/Reject suggestions in the OWL panel.
            partner_id = self._suggested_vendor_id(extraction)
            write_vals = {
                "extraction_json": json.dumps(payload),
                "extraction_model": result["model"],
                "ai_extracted_json": payload,
                "ai_extracted_total": float(extraction.amount_total),
                "ai_confidence": 0.0,  # no confidence channel yet in schema
                "ai_review_required": True,
                "ai_extraction_status": "extracted",
            }
            if partner_id:
                write_vals["partner_id"] = partner_id
            if extraction.invoice_date:
                write_vals["invoice_date"] = extraction.invoice_date.isoformat()
            if extraction.due_date:
                write_vals["invoice_date_due"] = extraction.due_date.isoformat()

            # Replace stale per-field rows with the fresh suggestions.
            if self.extraction_line_ids:
                self.extraction_line_ids.unlink()
            line_vals = [
                (0, 0, line) for line in self._suggested_field_lines(payload)
            ]
            if line_vals:
                write_vals["extraction_line_ids"] = line_vals
            self.write(write_vals)

            # Persist the token/cost ledger row for this extraction. The AI
            # spend view (invoice.agent.usage) is grouped by this data and
            # shows month-to-date cost; the cache_read counter is the proof
            # that prompt caching actually hit on repeat calls.
            self.env["invoice.llm.service"].log_usage(
                self.id,
                result["usage"],
                model=result["model"],
            )

            _logger.info(
                "invoice_agent suggest: move_id=%d model=%s usage=%s",
                self.id,
                result["model"],
                result["usage"],
            )
            return self._suggest_notification(
                "success",
                _("Extraction complete"),
                _(
                    "Suggested values for %(summary)s. Review each chip in the "
                    "AI Suggestion panel and accept what looks right.",
                )
                % {"summary": summary},
            )
        except AIServiceUnavailable as exc:
            # The AI service is down / rate-limited (503). Do NOT mark the
            # bill permanently failed — flip it back to a retryable state so
            # the ir.cron worker re-runs it once the service recovers.
            _logger.warning(
                "invoice_agent suggest deferred (service unavailable) for %s: %s",
                self.display_name,
                exc,
            )
            self.write(
                {
                    "ai_extraction_status": "pending",
                    "ocr_state": "pending",
                    "ai_error_message": str(exc)[:2000],
                },
            )
            return self._suggest_notification(
                "warning",
                _("Extraction queued for retry"),
                str(exc),
            )
        except Exception as exc:
            _logger.warning(
                "invoice_agent suggest failed for %s: %s",
                self.display_name,
                exc,
            )
            self.write(
                {
                    "ai_extraction_status": "failed",
                    "ai_error_message": str(exc),
                },
            )
            return self._suggest_notification(
                "danger",
                _("Extraction failed"),
                str(exc),
            )

    @api.model
    def _suggest_notification(self, notification_type, title, message):
        """Build the ir.actions.client toast the header button returns."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "sticky": False,
                "type": notification_type,
            },
        }

    def apply_suggested_value(self, field_name):
        """Apply exactly one suggested value onto the move.

        Called by the OWL Accept chip. The value is re-read from the
        persisted ``extraction_json`` payload — the client only sends the
        field name, so a spoofed payload can never reach the ORM write.
        Removes the Awaited suggestion row once applied.
        """
        self.ensure_one()
        if not self.extraction_json:
            raise UserError(_("No extraction payload to apply from."))
        payload = json.loads(self.extraction_json or "{}")

        if field_name == "vendor_name":
            vendor_name = payload.get("vendor_name")
            if not vendor_name:
                raise UserError(_("No vendor_name suggestion stored."))
            partner = self.env["res.partner"]
            if payload.get("vendor_vat"):
                partner = partner.search(
                    [("vat", "=", payload["vendor_vat"]), ("parent_id", "=", False)],
                    limit=1,
                )
            if not partner:
                partner = partner.search(
                    [("name", "ilike", vendor_name), ("parent_id", "=", False)],
                    limit=1,
                )
            if not partner:
                raise UserError(
                    _(
                        "No vendor matches '%s'. Create the partner first, then apply.",
                        vendor_name,
                    ),
                )
            self.write({"partner_id": partner.id})
        elif field_name == "invoice_date":
            self.write({"invoice_date": payload.get("invoice_date")})
        elif field_name == "due_date":
            self.write({"invoice_date_due": payload.get("due_date")})
        elif field_name == "amount_total":
            # Totals are computed from lines on a bill — applying the
            # suggested total means applying the suggested line items.
            self._apply_suggested_lines(payload.get("lines") or [])
            self.write({"ai_extracted_total": float(payload.get("amount_total") or 0.0)})
        elif field_name.startswith("line:"):
            index = int(field_name.split(":", 1)[1])
            lines = payload.get("lines") or []
            if index >= len(lines):
                raise UserError(_("Suggested line %s no longer exists.", field_name))
            self._apply_suggested_lines([lines[index]])
        elif field_name in ("subtotal", "tax_total", "currency", "vendor_vat"):
            # Extraction metadata: fold back into the persisted payload.
            if payload.get(field_name) is not None:
                payload[field_name] = self._json_value(payload[field_name])
                self.write({"extraction_json": json.dumps(payload)})
        else:
            raise UserError(_("Unknown suggestion field: %s", field_name))

        suggestion = self.extraction_line_ids.filtered(
            lambda row: row.field_name == field_name,
        )
        if suggestion:
            suggestion.unlink()
        return True

    def _json_value(self, value):
        """Normalize a payload value into a JSON-safe scalar."""
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _apply_suggested_lines(self, lines):
        """Write suggested line items onto the bill (replacing current ones).

        Used by ``apply_suggested_value('amount_total')`` and by individual
        ``line:N`` chips. Keeps Odoo's computed amounts as the source of
        truth for the real total.
        """
        self.ensure_one()
        if not lines:
            raise UserError(_("The extraction did not suggest any lines."))
        line_vals = []
        for line in lines:
            try:
                price_unit = float(line.get("price_unit") or 0.0)
                quantity = float(line.get("quantity") or 1.0)
            except (TypeError, ValueError):
                price_unit = 0.0
                quantity = 1.0
            line_vals.append(
                (0, 0, {
                    "name": line.get("name") or "Suggested line",
                    "price_unit": price_unit,
                    "quantity": quantity,
                }),
            )
        self.write({"invoice_line_ids": line_vals})

    # -------------------------------------------------------------------------
    # VENDOR MATCHING
    # -------------------------------------------------------------------------
    def _match_vendor(self):
        self.ensure_one()
        if not self.ai_extracted_json:
            return None
        payload = self.ai_extracted_json
        partner_obj = self.env["res.partner"]
        vat = payload.get("vat") or payload.get("tax_id") or payload.get("company_vat")
        if vat:
            partner = partner_obj.search(
                [("vat", "=", vat), ("parent_id", "=", False)],
                limit=1,
            )
            if partner:
                return partner
        company_name = (
            payload.get("company_name")
            or payload.get("supplier_name")
            or payload.get("vendor_name")
        )
        if company_name:
            partner = partner_obj.search(
                [("name", "ilike", company_name), ("parent_id", "=", False)],
                limit=1,
            )
            if partner:
                return partner
        return None

    @api.onchange("ai_ocr_text")
    def _onchange_ai_ocr_text(self):
        if not self.ai_ocr_text:
            return {}
        if not self.ai_extracted_json:
            return {}
        partner = self._match_vendor()
        if partner:
            self.partner_id = partner
            return {}
        return {
            "warning": {
                "title": _("Vendor Not Matched"),
                "message": _(
                    "Could not automatically match a vendor from the AI-extracted data. "
                    "Please select the vendor manually from the list.",
                ),
            },
        }

    # -------------------------------------------------------------------------
    # ORM Overrides
    # -------------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if "ai_extraction_status" in vals:
            if vals["ai_extraction_status"] == "validated":
                self.write({"ai_validated_on": fields.Datetime.now()})
            elif vals["ai_extraction_status"] == "extracted":
                self.write({"ai_extracted_on": fields.Datetime.now()})
        return res

    # -------------------------------------------------------------------------
    # EXTRACTION STATE MACHINE: enqueue hook
    # -------------------------------------------------------------------------
    def _invoice_agent_schedule_extraction(self):
        """Enqueue this move for background OCR + Claude extraction.

        Called by the /invoice_agent/upload controller right after the draft
        bill is created with ``ai_extraction_status='pending'``. In this
        exercise the worker is a placeholder: keeping the status at
        'pending' (or flipping it to 'processing') is enough for clients to
        poll /invoice_agent/status/<id> while the real pipeline runs.

        Override this method in a fully wired deployment to push a job to the
        queue (e.g. an ir.cron tick, a bus.Bus message, or an external worker
        consuming the attachment) and to set 'processing'.
        """
        self.ensure_one()
        if self.ai_extraction_status != "pending":
            return
        # Placeholder: mark processing so the queue view and the status
        # endpoint show something meaningful. A real implementation would
        # hand the attachment to the OCR worker instead of blocking here.
        self.write({"ai_extraction_status": "processing"})

    # -------------------------------------------------------------------------
    # CRON: Retry stuck extractions
    # -------------------------------------------------------------------------
    @api.model
    def _cron_retry_stuck_extractions(self):
        """Called by ir.cron every 30 minutes.

        Resets two kinds of stuck records back to a retryable state:

        * ``ai_extraction_status='processing'`` for more than 1 hour
          -> reset to 'pending' (Claude pipeline).
        * ``ocr_state='running'`` for more than 1 hour -> reset to 'pending'
          (OCR cron worker crashed mid-job, e.g. the container was restarted
          between the 'running' write and the final commit).
        """
        threshold = fields.Datetime.now() - timedelta(hours=1)
        count = 0

        stuck_extractions = self.search(
            [
                ("ai_extraction_status", "=", "processing"),
                ("write_date", "<", threshold),
            ],
        )
        for move in stuck_extractions:
            try:
                move.write(
                    {
                        "ai_extraction_status": "pending",
                        "ai_confidence": 0.0,
                    },
                )
                count += 1
            except Exception:
                _logger.exception(
                    "Cron failed to reset stuck extraction on %s",
                    move.display_name,
                )

        stuck_ocr = self.search(
            [
                ("ocr_state", "=", "running"),
                ("write_date", "<", threshold),
            ],
        )
        for move in stuck_ocr:
            try:
                move.write({"ocr_state": "pending"})
                count += 1
            except Exception:
                _logger.exception(
                    "Cron failed to reset stuck OCR on %s",
                    move.display_name,
                )

        if stuck_extractions or stuck_ocr:
            _logger.info(
                "_cron_retry_stuck_extractions: reset %d stuck moves "
                "(%d extraction, %d OCR) to pending",
                count,
                len(stuck_extractions),
                len(stuck_ocr),
            )
        return count

    # -------------------------------------------------------------------------
    # OCR CRON WORKER: claim pending records in batches, commit per record
    # -------------------------------------------------------------------------
    # Called by the ``invoice_agent.cron_ocr_pending`` ir.cron (see
    # data/cron.xml). A twenty-second OCR job must never run inside an HTTP
    # worker — the cron keeps the work off the request path and bounds how
    # many concurrent workers can hit Tesseract at once.
    #
    # Contract with the cron caller:
    # * ``_cron_ocr_pending_bills(batch_size=10)`` is an ``@api.model``
    #   method: cron invokes ``model._cron_ocr_pending_bills()`` with no
    #   recordset and gets back a plain int (count of moves processed).
    # * Batching: only ``batch_size`` moves are claimed per cron tick. With
    #   ``max_cron_threads`` capped in odoo.conf and a modest batch size,
    #   peak Tesseract concurrency stays bounded so the container never OOMs
    #   under a pile of uploaded scans.
    # * Per-record commit: each move is processed inside its own
    #   ``self.env.cr.commit()`` window. One blank scan or corrupt PDF marks
    #   only that move ``ocr_state='failed'`` and commits; the rest of the
    #   batch continues. Without this, a single bad attachment would roll
    #   back the entire batch on error.
    # -------------------------------------------------------------------------
    @api.model
    def _cron_ocr_pending_bills(self, batch_size=10):
        """Claim up to ``batch_size`` pending OCR moves and process each one.

        Returns the number of moves processed. Never raises: per-move
        failures degrade the move to ``ocr_state='failed'`` with
        ``ocr_error_message`` set, so a bad scan cannot take down the cron
        or poison the rest of the batch.
        """
        moves = self.search(
            [("ocr_state", "=", "pending"), ("ai_source_attachment_id", "!=", False)],
            order="write_date asc, id asc",
            limit=batch_size,
        )
        processed = 0
        for move in moves:
            try:
                self.env.cr.commit()  # fresh txn per record — see contract above
                move._ocr_process_one(move.id)
                processed += 1
            except Exception:
                _logger.exception(
                    "OCR cron failed for move %s — marked failed and continuing",
                    move.display_name,
                )
            finally:
                self.env.cr.rollback()
                self.env.cr.commit()
        return processed

    def _ocr_process_one(self, move_id):
        """Run OCR for one move, storing text + confidence on success.

        Claimed and committed by ``_cron_ocr_pending_bills``; this method
        never calls commit itself. State flow: pending -> running -> done,
        or pending -> running -> failed on any error (guard violations from
        ``invoice.ocr.service`` included).
        """
        move = self.browse(move_id)
        if not move.exists() or move.ocr_state != "pending":
            return
        attachment = move.ai_source_attachment_id
        move.write({"ocr_state": "running", "ocr_error_message": False})
        try:
            result = self.env["invoice.ocr.service"]._extract_text(attachment)
            move.write(
                {
                    "ocr_state": "done",
                    "ocr_text": result["text"],
                    "ocr_confidence": result["confidence"],
                    "ocr_engine": "tesseract",
                    # Mirror the extracted text back into the legacy AI
                    # pipeline field so ``action_suggest_extraction`` reuses
                    # the OCR result instead of re-running Tesseract.
                    "ai_ocr_text": result["text"],
                },
            )
            _logger.info(
                "invoice_agent OCR done move_id=%d conf=%.2f len=%d",
                move.id,
                result["confidence"],
                len(result["text"]),
            )
        except Exception as exc:
            move.write(
                {
                    "ocr_state": "failed",
                    "ocr_error_message": str(exc)[:2000],
                },
            )
            _logger.warning(
                "invoice_agent OCR failed move_id=%d: %s",
                move.id,
                exc,
            )

    # -------------------------------------------------------------------------
    # EXTRACTION PIPELINE: OCR -> Claude -> normalize -> write
    # -------------------------------------------------------------------------
    # ``_run_extraction`` is the queue-side twin of the upload endpoint: it
    # consumes a move stuck in 'processing', calls the (mockable) Claude
    # client and writes back the normalized fields. Every failure degrades the
    # move to ``ai_extraction_status='failed'`` with ``ai_error_message`` set —
    # the pipeline never raises through the caller.
    # -------------------------------------------------------------------------
    def _invoice_agent_ocr(self):
        """Return OCR text for the source attachment.

        Prefers an already-stored ``ai_ocr_text`` (set on re-runs or seeded by
        tests), then falls back to Tesseract on the source PDF. Any failure
        degrades to an empty string — a missing PDF must not crash the worker.
        """
        self.ensure_one()
        if self.ai_ocr_text:
            return self.ai_ocr_text
        attachment = self.ai_source_attachment_id
        if not attachment:
            return ""
        try:
            import pytesseract
            from PIL import Image

            raw = attachment.raw
            if isinstance(raw, str):
                raw = base64.b64decode(raw)
            return pytesseract.image_to_string(Image.open(io.BytesIO(raw))) or ""
        except Exception:
            _logger.warning(
                "invoice_agent OCR unavailable for %s — continuing with empty text",
                self.display_name,
            )
            return ""

    def _claude_messages_create(self, ocr_text, model="claude-sonnet-4-5"):
        """Call the Anthropic Messages API with the structured-output prompt.

        Isolated behind this one method so tests can patch it with
        ``unittest.mock.patch`` and a frozen ``claude_response.json`` fixture —
        the test suite never touches the network.
        """
        import anthropic

        client = anthropic.Anthropic()
        return client.messages.create(
            model=model,
            max_tokens=1024,
            system=_CLAUDE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": ocr_text or "No OCR text available",
                },
            ],
        )

    def _parse_claude_payload(self, raw_text):
        """Normalize a Claude structured-output answer into the extraction dict.

        Input: the JSON text Claude returned. Output dict keys (documented in
        ``docs/api.md``):

        * ``extracted_vendor_id`` — matched ``res.partner`` id (0 when unknown)
        * ``extraction_confidence`` — float 0..1 (None when absent)
        * ``lines`` — ``[{name, quantity, price_unit, confidence}]``
        * ``notes``, ``amount_total``, ``invoice_date``, ``invoice_date_due``,
          ``ref``, ``review_required``, ``model_used``

        Malformed JSON or a non-object answer raises ``ValueError``; the
        caller (:meth:`_run_extraction`) degrades the move to 'failed' instead
        of crashing.
        """
        try:
            data = json.loads(raw_text or "")
        except (TypeError, ValueError) as exc:
            raise ValueError("Claude returned malformed JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("Claude returned a non-object payload")

        confidence = data.get("overall_confidence", data.get("confidence"))
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError) as exc:
                raise ValueError("Claude returned an invalid overall_confidence") from exc

        # Vendor resolution: explicit id wins, name fallback mirrors
        # _match_vendor on res.partner.
        vendor = self.env["res.partner"]
        vendor_id = data.get("extracted_vendor_id") or data.get("vendor_id")
        if vendor_id:
            candidate = vendor.browse(vendor_id)
            if candidate.exists():
                vendor = candidate
        if not vendor:
            company_name = (
                data.get("company_name")
                or data.get("supplier_name")
                or data.get("vendor_name")
            )
            if company_name:
                vendor = vendor.search(
                    [("name", "ilike", company_name), ("parent_id", "=", False)],
                    limit=1,
                )

        payload = {
            "extracted_vendor_id": vendor.id or None,
            "extraction_confidence": confidence,
            "lines": data.get("lines") or [],
            "notes": data.get("notes"),
            "amount_total": data.get("amount_total"),
            "invoice_date": data.get("invoice_date"),
            "invoice_date_due": data.get("invoice_date_due"),
            "ref": data.get("ref"),
            "review_required": bool(data.get("review_required")),
            "model_used": data.get("model_used"),
        }
        for source_key in ("company_name", "supplier_name", "vendor_name", "vat"):
            if data.get(source_key):
                payload[source_key] = data[source_key]
        return payload

    def _apply_extraction_payload(self, payload):
        """Write a normalized extraction payload onto the move.

        Scores the payload through ``invoice.llm.service.score_extraction``
        (arithmetic + VAT/IBAN rescue + self-report blend) and routes the
        move: a sub-threshold score flags ``ai_review_required`` and posts
        the reason + notes on the chatter — the bill is drafted, never
        silently posted.
        """
        self.ensure_one()
        ocr_text = self.ocr_text or self.ai_ocr_text
        score, details = self.env["invoice.llm.service"].score_extraction(
            payload,
            ocr_text=ocr_text,
            ocr_confidence=self.ocr_confidence,
        )
        # Keep the rescued payload (VAT/IBAN filled from the OCR text) as the
        # audit source of truth for this run.
        payload = details.get("rescued_payload") or payload

        # NOTE: confidence_score / ai_confidence_details / ai_confidence_notes
        # are stored *computed* fields — never write them directly. They
        # regenerate from the inputs below (ai_extracted_json, ai_confidence,
        # ocr_*) through ``_compute_confidence_score``, which re-runs the
        # same deterministic blend and reproduces this exact audit trail.
        vals = {
            # NOTE: ai_ocr_text is intentionally NOT written here — the OCR
            # cron already stored the raw text (see _ocr_process_one) and the
            # confidence compute re-scores against it.
            "ai_extracted_json": payload,
            "ai_extracted_total": payload.get("amount_total"),
            "ai_review_required": bool(payload.get("review_required")),
            "ai_extraction_status": "extracted",
            "ai_confidence": score,
        }
        if payload.get("extracted_vendor_id"):
            vals["partner_id"] = payload["extracted_vendor_id"]
        for field_name in ("invoice_date", "invoice_date_due", "ref"):
            if payload.get(field_name):
                vals[field_name] = payload[field_name]

        line_vals = []
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            try:
                price_unit = float(line.get("price_unit") or 0.0)
                quantity = float(line.get("quantity") or 1.0)
            except (TypeError, ValueError):
                price_unit = 0.0
                quantity = 1.0
            line_vals.append(
                (0, 0, {
                    "name": line.get("name") or "Imported line",
                    "price_unit": price_unit,
                    "quantity": quantity,
                    "ai_confidence": line.get("confidence"),
                }),
            )
        if line_vals:
            vals["invoice_line_ids"] = line_vals
        self.write(vals)  # write() stamps ai_extracted_on on status change

        # Route: sub-threshold or pipeline-flagged extractions must land in
        # Needs Review with the reason visible on the chatter.
        threshold = (
            self.journal_id.ai_min_confidence
            if self.journal_id.ai_agent_enabled
            else 0.70
        )
        if self.ai_review_required or score < threshold:
            self._flag_needs_review(
                reason=(
                    "extracted confidence %.0f%% is below the %.0f%% journal "
                    "threshold"
                    % (score * 100, threshold * 100)
                ),
            )

    # -------------------------------------------------------------------------
    # MAP: Pydantic extraction -> account.move ORM values dict
    # -------------------------------------------------------------------------
    # Tolerance used when comparing the sum of the extracted lines against the
    # extracted grand total. A cent-sized rounding discrepancy is normal on
    # real invoices; anything larger means the extraction is internally
    # inconsistent and the record must not be created.
    EXTRACTION_LINE_SUM_TOLERANCE = 0.01

    @api.model
    def _map_extraction_to_move(self, extraction):
        """Convert a schema-validated ``InvoiceExtraction`` into ORM values.

        The single place that turns the Pydantic object into an
        ``account.move`` values dict. Handles three conversions the ORM
        cannot do by itself:

        * ``fields.Date`` — pydantic returns ``datetime.date`` objects; the
          ORM (and JSON serialization) wants ``YYYY-MM-DD`` strings.
        * ``currency_id`` — the extraction carries an ISO-4217 code
          (``res.currency.name`` in the main branch). An un-resolvable code
          leaves the currency empty (the company currency applies) instead of
          guessing the wrong currency.
        * line sum vs ``amount_total`` — an extraction whose lines do not add
          up to the printed grand total is internally inconsistent and is
          rejected with a ``ValidationError`` rather than persisted.

        :param extraction: validated ``InvoiceExtraction`` pydantic model.
        :return: dict of ORM values for ``account.move.create()``.
        :raises ValidationError: when the line sum diverges from
            ``amount_total`` beyond the tolerance.
        """
        payload = self.env["invoice.llm.service"].extraction_to_dict(extraction)
        lines = payload.get("lines") or []

        # ---- Balance check: sum(price_unit * quantity) == amount_total ----
        line_sum = sum(
            float(line.get("quantity") or 1.0) * float(line.get("price_unit") or 0.0)
            for line in lines
        )
        # Lines add up to the *subtotal* on a taxed invoice; only
        # grand-total-only layouts must match amount_total directly.
        balance_target = payload.get("subtotal")
        if balance_target is None:
            balance_target = payload.get("amount_total")
        balance_target = float(balance_target or 0.0)
        if abs(line_sum - balance_target) > self.EXTRACTION_LINE_SUM_TOLERANCE:
            raise ValidationError(
                _(
                    "Extraction rejected for '%s': the line items sum to "
                    "%.2f but the extracted subtotal/total is %.2f. Refusing "
                    "to create an inconsistent bill.",
                    payload.get("vendor_name") or "unknown vendor",
                    line_sum,
                    balance_target,
                ),
            )

        # ---- Resolve the vendor: VAT first, then fuzzy name, else empty ----
        partner = self.env["res.partner"]
        if extraction.vendor_vat:
            partner = partner.search(
                [("vat", "=", extraction.vendor_vat), ("parent_id", "=", False)],
                limit=1,
            )
        if not partner and extraction.vendor_name:
            partner = partner.search(
                [("name", "ilike", extraction.vendor_name), ("parent_id", "=", False)],
                limit=1,
            )

        # ---- Resolve the currency from the ISO-4217 code ----
        currency = self.env["res.currency"]
        if extraction.currency:
            currency = currency.search([("name", "=", extraction.currency)], limit=1)

        # ---- Calibrated confidence (week 7) --------------------------------
        # Score the payload through the deterministic blend (self-report +
        # arithmetic + VAT/IBAN rescue) so the draft bill carries a real
        # confidence_score from creation. OCR text is applied by the
        # orchestrator later; without it the OCR/rescue terms stay neutral
        # and the score reflects the self-report + line-sum check.
        score, details = self.env["invoice.llm.service"].score_extraction(
            payload,
            ocr_text=None,
            ocr_confidence=0.5,
        )

        invoice_line_vals = []
        for line in lines:
            try:
                price_unit = float(line.get("price_unit") or 0.0)
                quantity = float(line.get("quantity") or 1.0)
            except (TypeError, ValueError):
                price_unit = 0.0
                quantity = 1.0
            invoice_line_vals.append(
                (0, 0, {
                    "name": line.get("name") or "Imported line",
                    "price_unit": price_unit,
                    "quantity": quantity,
                    "ai_confidence": line.get("confidence"),
                }),
            )

        vals = {
            "move_type": "in_invoice",
            "partner_id": partner.id or False,
            "invoice_date": (
                fields.Date.to_string(extraction.invoice_date)
                if extraction.invoice_date
                else False
            ),
            "invoice_date_due": (
                fields.Date.to_string(extraction.due_date)
                if extraction.due_date
                else False
            ),
            "invoice_line_ids": invoice_line_vals,
            # The move is created as a draft — it is never posted by the
            # pipeline. Routing: only extractions scoring at/above the
            # journal threshold ride the Auto kanban column; everything else
            # is flagged (review_required) and lands in Needs Review.
            #
            # NOTE: confidence_score / details / notes are stored *computed*
            # fields and regenerate from the inputs below through
            # ``_compute_confidence_score`` — never write them here.
            "ai_extraction_status": "extracted",
            "ai_confidence": score,
            "ai_review_required": score < (
                self.journal_id.ai_min_confidence
                if self.journal_id.ai_agent_enabled
                else 0.70
            ),
            "ai_extracted_total": amount_total,
            "ai_extracted_json": payload,
            "extraction_json": json.dumps(payload),
        }
        if currency:
            vals["currency_id"] = currency.id

        _logger.info(
            "invoice_agent _map_extraction_to_move: vendor=%s lines=%d sum=%.2f total=%.2f",
            payload.get("vendor_name"),
            len(invoice_line_vals),
            line_sum,
            amount_total,
        )
        return vals

    # -------------------------------------------------------------------------
    # ORCHESTRATOR: OCR -> Claude -> map -> create
    # -------------------------------------------------------------------------
    @api.model
    def _create_move_from_extraction(self, attachment, ocr_text=None):
        """Run the full OCR → LLM → map → create chain for one attachment.

        This is the queue-side twin of ``_run_extraction`` for the *upload*
        path where no move exists yet: the controller stores the attachment
        and hands it here; the chain produces a complete draft ``account.move``
        with partner, dates, lines and taxes resolved.

        Chain (see task brief):
            ocr_service._extract_text(attachment)
              -> llm_service.extract_invoice(ocr_text)
              -> _map_extraction_to_move(extraction)
              -> env['account.move'].create(vals)

        Vendor matching follows the VAT-first, fuzzy-name-second rule and
        leaves ``partner_id`` empty rather than guessing the wrong vendor.

        :param attachment: ``ir.attachment`` holding the scanned PDF/image.
        :param ocr_text: optional pre-computed OCR text (skips the OCR pass).
        :return: the created ``account.move`` record (draft, never posted).
        :raises ValidationError: on an inconsistent extraction (line sum);
            other failures are left to the caller to degrade.
        """
        attachment = attachment.exists() if attachment else attachment
        if not attachment:
            raise UserError(_("No source attachment to extract from."))
        if ocr_text is None:
            ocr_result = self.env["invoice.ocr.service"]._extract_text(attachment)
            ocr_text = ocr_result["text"]

        result = self.env["invoice.llm.service"].extract_invoice(ocr_text)
        extraction = result["parsed"]
        vals = self._map_extraction_to_move(extraction)
        vals.update(
            {
                "ai_source_attachment_id": attachment.id,
                "ai_ocr_text": ocr_text,
                "ocr_state": "done",
                "ocr_text": ocr_text,
                "extraction_model": result.get("model"),
            },
        )
        move = self.create(vals)

        # Persist the token ledger row for auditability / cost tracking.
        try:
            self.env["invoice.llm.service"].log_usage(
                move.id,
                result.get("usage") or {},
                model=result.get("model"),
            )
        except Exception:
            _logger.exception(
                "invoice_agent failed to log usage for move_id=%s", move.id,
            )

        _logger.info(
            "invoice_agent orchestrator: created move_id=%d total=%s",
            move.id,
            move.amount_total,
        )
        return move

    # -------------------------------------------------------------------------
    # HIGH-EFFORT SECOND PASS (week 7 fallback)
    # -------------------------------------------------------------------------
    # Sub-threshold extractions get one more Claude pass with
    # ``effort='high'`` (mapped to ``output_config={'effort': 'high'}`` in
    # the LLM service). Only the *lowest* score triggers it, and only once —
    # ``ai_confidence_details['checks']`` records ``"high_effort"`` so a
    # re-run never loops. The second pass runs through the same
    # ``score_extraction`` blend; if the re-scored payload still sits below
    # the journal threshold the move is flagged for Needs Review.
    # -------------------------------------------------------------------------
    def _run_high_effort_pass(self, threshold):
        """Re-extract with effort='high' and re-score the move.

        :return: True when the high-effort pass produced a better score.
        """
        self.ensure_one()
        ocr_text = self.ocr_text or self.ai_ocr_text
        if not ocr_text:
            return False
        try:
            result = self.env["invoice.llm.service"].extract_invoice(
                ocr_text,
                effort="high",
            )
        except Exception as exc:
            _logger.warning(
                "invoice_agent high-effort pass failed for %s: %s",
                self.display_name,
                exc,
            )
            return False

        extraction = result.get("parsed")
        if extraction is None:
            return False
        payload = self.env["invoice.llm.service"].extraction_to_dict(extraction)
        score, details = self.env["invoice.llm.service"].score_extraction(
            payload,
            ocr_text=ocr_text,
            ocr_confidence=self.ocr_confidence,
            checks=["high_effort"],
        )
        previous = self.confidence_score or 0.0
        _logger.info(
            "invoice_agent high-effort pass: move_id=%d score %.2f -> %.2f "
            "threshold %.2f usage=%s",
            self.id,
            previous,
            score,
            threshold,
            result.get("usage"),
        )
        if score <= previous:
            # The second pass did not improve certainty — keep the original
            # extraction and route to review as before.
            return False

        self._apply_extraction_payload(payload)
        # The improvement is already recorded via _apply_extraction_payload;
        # append the provenance so the audit trail shows which path fired.
        details = dict(self.ai_confidence_details or {})
        checks = list(details.get("checks") or [])
        if "high_effort" not in checks:
            checks.append("high_effort")
            details["checks"] = checks
            self.write({"ai_confidence_details": details})
        try:
            self.env["invoice.llm.service"].log_usage(
                self.id,
                result.get("usage") or {},
                model=result.get("model"),
            )
        except Exception:
            _logger.exception(
                "invoice_agent failed to log high-effort usage for move_id=%s",
                self.id,
            )
        return score > previous

    # -------------------------------------------------------------------------
    # EXTRACTION QUEUE CRON: consume processed moves through the pipeline
    # -------------------------------------------------------------------------
    @api.model
    def _cron_extract_pending_bills(self, batch_size=10):
        """Claim moves with OCR done + extraction 'processing' and run them.

        Mirrors ``_cron_ocr_pending_bills``: bounded batch, per-record
        isolation, never raises. Each move flows through
        ``_run_extraction`` and, when the first pass scores below the
        journal threshold, one ``_run_high_effort_pass`` before being
        routed to Auto / Needs Review.
        """
        moves = self.search(
            [
                ("ai_extraction_status", "=", "processing"),
                ("ocr_state", "=", "done"),
            ],
            order="write_date asc, id asc",
            limit=batch_size,
        )
        processed = 0
        for move in moves:
            try:
                self.env.cr.commit()
                move._run_extraction()
                if move.ai_extraction_status == "extracted" and (
                    move.confidence_score or 0.0
                ) < move._get_ai_min_confidence():
                    try:
                        move._run_high_effort_pass(move._get_ai_min_confidence())
                    except Exception:
                        _logger.exception(
                            "High-effort pass crashed for move_id=%d — "
                            "original extraction stands",
                            move.id,
                        )
                processed += 1
            except Exception:
                _logger.exception(
                    "Extraction cron failed for move %s — marked failed and "
                    "continuing",
                    move.display_name,
                )
            finally:
                self.env.cr.rollback()
                self.env.cr.commit()
        return processed

    def _run_extraction(self):
        """Run the OCR → Claude → normalize pipeline on moves in 'processing'.

        The Claude call is isolated in :meth:`_claude_messages_create`, which
        tests replace with a frozen fixture. Malformed answers or client
        errors degrade the move to ``ai_extraction_status='failed'`` and set
        ``ai_error_message``; they never propagate.
        """
        for move in self:
            if move.ai_extraction_status != "processing":
                continue
            move.write({"ai_error_message": False})
            try:
                ocr_text = move._invoice_agent_ocr()
                response = move._claude_messages_create(ocr_text)
                raw_text = response.content[0].text
                payload = move._parse_claude_payload(raw_text)
                move._apply_extraction_payload(payload)
            except AIServiceUnavailable as exc:
                # The AI service is down / rate-limited (503): the move stays
                # retryable — flip it back to pending so the next cron tick
                # re-runs it, instead of marking it permanently failed.
                _logger.warning(
                    "invoice_agent extraction deferred (service unavailable) "
                    "for %s: %s",
                    move.display_name,
                    exc,
                )
                move.write(
                    {
                        "ai_extraction_status": "pending",
                        "ocr_state": "pending",
                        "ai_error_message": str(exc)[:2000],
                    },
                )
            except Exception as exc:
                _logger.warning(
                    "invoice_agent extraction failed for %s: %s",
                    move.display_name,
                    exc,
                )
                move.write(
                    {
                        "ai_extraction_status": "failed",
                        "ai_error_message": str(exc),
                    },
                )

    # -------------------------------------------------------------------------
    # EXTERNAL API FACADE: create_from_extraction
    # -------------------------------------------------------------------------
    # One stable entry point for XML-RPC and /json/2 callers, instead of raw
    # ORM writes scattered across integrations. The contract (payload fields,
    # field mapping, error codes) is documented in ``docs/api.md``.
    # -------------------------------------------------------------------------
    @api.model
    def create_from_extraction(self, payload):
        """Create a draft vendor bill from an externally-provided extraction.

        This is an ``@api.model`` method: both XML-RPC and the Odoo 19
        ``/json/2/account.move/create_from_extraction`` endpoint call it
        *without* a record id and get back a plain, JSON-serializable dict —
        never a recordset.

        :param payload: dict following the contract in ``docs/api.md``
        :return: ``{"success": True, "id": ..., "name": ...,
                    "ai_extraction_status": "pending"}`` on success, or
                 ``{"success": False, "error_code": "E4xxx",
                    "message": "..."}`` on failure.
        """
        if not isinstance(payload, dict):
            return self._facade_error("E4001", "payload must be a JSON object")

        # ---- Validate the line items ----
        lines = payload.get("lines")
        if not isinstance(lines, list) or not lines:
            return self._facade_error(
                "E4002",
                "payload['lines'] must be a non-empty list of line objects",
            )
        for index, line in enumerate(lines):
            if not isinstance(line, dict):
                return self._facade_error(
                    "E4003",
                    f"payload['lines'][{index}] must be an object",
                )
            if not (line.get("name") or line.get("product_id")):
                return self._facade_error(
                    "E4003",
                    f"payload['lines'][{index}] needs 'name' or 'product_id'",
                )

        # ---- Resolve the partner (explicit id wins over name matching) ----
        partner_id = payload.get("partner_id")
        if partner_id:
            partner = self.env["res.partner"].browse(partner_id)
            try:
                partner.check_access("read")
            except AccessError:
                return self._facade_error(
                    "E4004",
                    f"no read access to res.partner {partner_id}",
                )
            if not partner.exists():
                return self._facade_error(
                    "E4004",
                    f"res.partner {partner_id} does not exist",
                )
        else:
            partner_name = payload.get("partner_name") or payload.get("vendor_name")
            partner = (
                self.env["res.partner"]
                .search(
                    [("name", "ilike", partner_name), ("parent_id", "=", False)],
                    limit=1,
                )
                if partner_name
                else self.env["res.partner"]
            )

        # ---- Resolve the journal ----
        journal_id = payload.get("journal_id")
        if journal_id:
            journal = self.env["account.journal"].browse(journal_id)
            if not journal.exists():
                return self._facade_error(
                    "E4005",
                    f"account.journal {journal_id} does not exist",
                )

        # ---- Build and create the draft bill ----
        invoice_line_vals = []
        for line in lines:
            try:
                price_unit = float(line.get("price_unit") or 0.0)
                quantity = float(line.get("quantity") or 1.0)
            except (TypeError, ValueError):
                price_unit = 0.0
                quantity = 1.0
            invoice_line_vals.append(
                {
                    "name": line.get("name") or "Imported line",
                    "price_unit": price_unit,
                    "quantity": quantity,
                    "product_id": line.get("product_id"),
                    "tax_ids": [(6, 0, line.get("tax_ids") or [])],
                },
            )

        vals = {
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "invoice_date": payload.get("invoice_date"),
            "invoice_date_due": payload.get("invoice_date_due"),
            "ref": payload.get("ref"),
            "invoice_line_ids": [(0, 0, line) for line in invoice_line_vals],
            # The bill is created inside the extraction state machine in
            # 'pending'; a queue consumer (or a re-run) schedules the work.
            "ai_extraction_status": "pending",
            "ai_confidence": payload.get("overall_confidence"),
            "ai_extracted_total": payload.get("amount_total"),
            "ai_extracted_json": payload,
        }
        if journal_id:
            vals["journal_id"] = journal_id

        try:
            move = self.create(vals)
        except (ValidationError, ValueError) as exc:
            return self._facade_error("E4221", str(exc))

        _logger.info(
            "invoice_agent create_from_extraction: move_id=%d via %s",
            move.id,
            self.env.user.login,
        )
        return {
            "success": True,
            "id": move.id,
            "name": move.name or "DRAFT",
            "ai_extraction_status": move.ai_extraction_status,
        }

    @api.model
    def _facade_error(self, error_code, message):
        """Build the failure dict for :meth:`create_from_extraction` and keep
        the server-side audit trail."""
        _logger.warning("invoice_agent facade error %s: %s", error_code, message)
        return {
            "success": False,
            "error_code": error_code,
            "message": message,
        }

    _sql_constraints = [
        (
            "check_ai_confidence_range",
            "CHECK(ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0))",
            "Overall AI Confidence score must strictly remain between 0.00 and 1.00.",
        ),
    ]
