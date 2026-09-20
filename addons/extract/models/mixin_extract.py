from __future__ import annotations

import logging
from typing import Any

from odoo import api, fields, models
from odoo.libs.documents import EXPENSIVE, Document

from ..tools import GENERATIVE, cascade
from ..tools.schema import known_schemas
from ..tools.source import document_of

_logger = logging.getLogger(__name__)

JOB_CHANNEL = "extract"

#: Returned by ``_extract_compare_value`` when a written value cannot be reduced
#: to something comparable with what was read. Distinct from ``None``, which is a
#: value a caller can legitimately write and which must still count as a
#: correction.
NOT_COMPARABLE = object()

WAIT_SECONDS = 30
WAIT_ATTEMPTS = 40

STATES = [
    ("none", "Not extracted"),
    ("queued", "Queued"),
    ("running", "Running"),
    ("waiting", "Waiting on a service"),
    ("done", "Extracted"),
    ("partial", "Partially extracted"),
    ("failed", "Failed"),
]


class MixinExtract(models.AbstractModel):
    _name = "mixin.extract"
    _description = "Document Extraction"

    _extract_document_type: str = ""
    _extract_target: dict[str, str] = {}

    extract_state = fields.Selection(
        selection=STATES,
        default="none",
        index=True,
        copy=False,
        readonly=True,
    )
    extract_result = fields.Json(
        copy=False,
        readonly=True,
        help="Every value that was read, with which strategy proposed it and "
        "how confident it was.",
    )
    extract_missing = fields.Json(
        copy=False,
        readonly=True,
        help="Required fields no strategy could read, and rules that do not "
        "hold. What a person has to supply.",
    )
    extract_error = fields.Text(
        copy=False,
        readonly=True,
    )
    extract_pending = fields.Json(
        copy=False,
        readonly=True,
        help="The service this document is waiting on, and its handle. Kept so "
        "the next attempt asks again rather than submitting the document a "
        "second time.",
    )
    extract_corrections = fields.Json(
        copy=False,
        readonly=True,
        help="Fields a person changed after extraction, with what was read and "
        "what it should have been.",
    )

    def write(self, vals):
        watched = set(self._extract_target.values()) & set(vals)
        corrections = {}
        if watched and not self.env.context.get("extracting"):
            for record in self:
                found = record._corrections_in(vals)
                if found:
                    corrections[record.id] = found

        result = super().write(vals)

        for record in self:
            found = corrections.get(record.id)
            if found:
                stored = dict(record.extract_corrections or {})
                stored.update(found)
                super(MixinExtract, record.with_context(extracting=True)).write(
                    {"extract_corrections": stored}
                )
        return result

    def _get_extract_document_type(self) -> str:
        return self._extract_document_type

    def _get_extract_source(self) -> Document | None:
        self.check_singleton()
        attachment = None
        if "message_main_attachment_id" in self._fields:
            attachment = self.message_main_attachment_id
        if not attachment:
            attachment = self.env["ir.attachment"].search(
                [("res_model", "=", self._name), ("res_id", "=", self.id)],
                order="id desc",
                limit=1,
            )
        if not attachment:
            return None
        # Not `attachment.raw`: that is empty for a blob a storage provider
        # holds, and gating on it refused to extract exactly the documents that
        # live in the cloud.
        content = attachment._fetch_content()
        if not content:
            return None
        return document_of(attachment, content)

    def _update_from_extraction(self, result) -> None:
        self.check_singleton()
        values = {}
        for schema_field, model_field in self._extract_target.items():
            if model_field not in self._fields:
                _logger.warning(
                    "%s maps %r to %r, which is not a field of this model",
                    self._name,
                    schema_field,
                    model_field,
                )
                continue
            value = result.flat().get(schema_field)
            if value is not None and not self[model_field]:
                values[model_field] = self._extract_write_value(model_field, value)
        if values:
            self.write(values)

    def _extract_write_value(self, model_field: str, value: Any) -> Any:
        """What to write for ``model_field`` given the scalar extraction read.

        Extraction yields scalars; a target that is not one (a relation the
        scalar has to be resolved against) overrides this. Returning the value
        unchanged is right for every plain column.
        """
        return value

    def _extract_compare_value(self, model_field: str, value: Any) -> Any:
        """The scalar to compare against what was read, for correction tracking.

        The inverse of ``_extract_write_value``: ``vals`` carries whatever the
        writer passed -- for a relation, command lists -- and comparing that to
        an extracted string would record every write as a correction. Return
        ``NOT_COMPARABLE`` to say the write cannot be reduced to a comparable
        value, which records nothing; ``None`` is a value like any other and
        still counts as a correction.
        """
        return value

    def action_extract(self):
        for record in self:
            record._extract_document(up_to=GENERATIVE)
        return True

    def action_extract_later(self):
        for record in self:
            record._extract_later()
        return True

    def _extract_later(self, delay: int = 0):
        self.check_singleton()
        job = self.delayed(
            channel=JOB_CHANNEL,
            eta=delay or None,
            identity_key=f"extract.{self._name}.{self.id}",
            name=f"Extract {self._get_extract_document_type()}: {self.display_name}",
        )._job_extract()
        self.extract_state = "queued"
        return job

    @api.job(channel=JOB_CHANNEL, max_retries=3, max_defers=WAIT_ATTEMPTS)
    def _job_extract(self) -> None:
        self.check_singleton()
        result = self._extract_document(up_to=GENERATIVE, allow_pending=True)
        if result is not None and result.waiting:
            self.env["ir.job"]._defer(
                WAIT_SECONDS,
                reason=f"{result.pending['strategy']} is still reading the document.",
            )

    def _extract_document(self, up_to: int = GENERATIVE, allow_pending: bool = False):
        self.check_singleton()
        doc_type = self._get_extract_document_type()
        if not doc_type:
            raise ValueError(
                f"{self._name} inherits mixin.extract without "
                "declaring _extract_document_type"
            )
        if doc_type not in known_schemas():
            raise ValueError(
                f"{self._name} declares document type {doc_type!r}, which no "
                f"module registers; known: {', '.join(known_schemas())}"
            )

        source = self._get_extract_source()
        if source is not None and allow_pending:
            source.options["read_up_to"] = EXPENSIVE
        if source is None:
            self.write(
                {
                    "extract_state": "failed",
                    "extract_error": "No document to read.",
                }
            )
            return None

        self.extract_state = "running"
        try:
            result = cascade.run(
                source,
                doc_type,
                env=self.env,
                up_to=up_to,
                allow_pending=allow_pending,
                pending=self.extract_pending or None,
            )
        except Exception as e:
            _logger.exception("Extraction failed on %s %s", self._name, self.id)
            self.write({"extract_state": "failed", "extract_error": str(e)})
            return None

        if result.waiting:
            self.write({"extract_state": "waiting", "extract_pending": result.pending})
            return result

        self.write(
            {
                "extract_pending": False,
                "extract_state": "done" if result.satisfied else "partial",
                "extract_result": _as_json(result),
                "extract_missing": {
                    "fields": list(result.missing),
                    "rules": list(result.violations),
                },
                "extract_error": False,
            }
        )
        self._update_from_extraction(result)
        return result

    def _corrections_in(self, vals: dict[str, Any]) -> dict[str, Any]:
        self.check_singleton()
        if not self.extract_result or not self._extract_target:
            return {}
        found = {}
        for schema_field, model_field in self._extract_target.items():
            if model_field not in vals:
                continue
            read = (self.extract_result or {}).get(schema_field)
            written = self._extract_compare_value(model_field, vals[model_field])
            if (
                not read
                or written is NOT_COMPARABLE
                or read.get("value") in (None, written)
            ):
                continue
            found[schema_field] = {
                "read": read.get("value"),
                "read_by": read.get("source"),
                "corrected_to": written,
            }
        return found


def _as_json(result) -> dict[str, Any]:
    return {
        name: {
            "value": field.value,
            "source": field.source,
            "confidence": field.confidence,
            "disputed": field.disputed,
            "candidates": [
                {"value": c.value, "source": c.source, "confidence": c.confidence}
                for c in field.candidates
            ],
        }
        for name, field in result.fields.items()
    }
