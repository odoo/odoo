import base64
import io
import json
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)

_CLAUDE_SYSTEM_PROMPT = (
    "You extract invoice data into strict JSON. Respond with ONLY a JSON "
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
    ai_extracted_json = fields.Json(
        string="AI Extracted Raw Payload",
        help="JSON blob containing full unprocessed OCR/AI response.",
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
    # CONSTRAINT: Validated status requires minimum confidence
    # -------------------------------------------------------------------------
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
        self.ensure_one()
        if self.journal_id.ai_agent_enabled:
            return self.journal_id.ai_min_confidence
        return 0.70

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
        Finds bills stuck in 'processing' for more than 1 hour
        and resets them to 'pending' so the extraction pipeline can retry.
        """
        threshold = fields.Datetime.now() - timedelta(hours=1)
        stuck = self.search(
            [
                ("ai_extraction_status", "=", "processing"),
                ("write_date", "<", threshold),
            ],
        )
        count = len(stuck)
        for move in stuck:
            try:
                move.write(
                    {
                        "ai_extraction_status": "pending",
                        "ai_confidence": 0.0,
                    },
                )
            except Exception:
                _logger.exception(
                    "Cron failed to reset stuck extraction on %s",
                    move.display_name,
                )
        if count:
            _logger.info(
                "_cron_retry_stuck_extractions: reset %d stuck moves from 'processing' to 'pending'",
                count,
            )
        return count

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
        """Write a normalized extraction payload onto the move."""
        self.ensure_one()
        vals = {
            "ai_ocr_text": payload.get("notes"),
            "ai_extracted_json": payload,
            "ai_extracted_total": payload.get("amount_total"),
            "ai_review_required": bool(payload.get("review_required")),
            "ai_extraction_status": "extracted",
        }
        if payload.get("extraction_confidence") is not None:
            vals["ai_confidence"] = payload["extraction_confidence"]
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
            "ai_ocr_text": payload.get("notes"),
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
