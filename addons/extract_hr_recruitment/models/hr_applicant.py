from __future__ import annotations

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.extract.models.mixin_extract import NOT_COMPARABLE

_debug = DebugLog(__name__)


def _ids_in_x2many(value):
    """The ids an x2many write adds, for the command shapes a write can carry."""
    if not isinstance(value, (list, tuple)):
        return []
    ids = []
    for command in value:
        if isinstance(command, int):
            ids.append(command)
        elif isinstance(command, (list, tuple)) and command:
            if command[0] == Command.SET:
                ids.extend(command[2])
            elif command[0] == Command.LINK:
                ids.append(command[1])
    return ids


class HrApplicant(models.Model):
    _name = "hr.applicant"
    _inherit = ["hr.applicant", "mixin.extract"]

    _extract_document_type = "resume"

    _extract_target = {
        "full_name": "partner_name",
        "email": "email_from",
        "phone": "phone_ids",
    }

    extract_can_be_read = fields.Boolean(compute="_compute_extract_can_be_read")

    def _extract_write_value(self, model_field, value):
        """Resolve a phone read off a CV into a ``phone.number``.

        An applicant's numbers are records, not a column: ``phone.number.create``
        reuses an existing record with the same sanitized number, so a CV that
        repeats a number the database already holds links it rather than
        duplicating it. A blank read writes nothing rather than creating a
        ``phone.number`` with no number in it.
        """
        if model_field == "phone_ids" and isinstance(value, str):
            if not value.strip():
                _debug.logic("cv_phone_ignored", reason="blank_read", applicant=self)
                return []
            phone = self.env["phone.number"].create({"number": value})
            _debug.lifecycle(
                "cv_phone_resolved",
                applicant=self,
                phone=phone,
                already_linked=phone in self.phone_ids,
            )
            return [Command.set(phone.ids)]
        return super()._extract_write_value(model_field, value)

    def _extract_compare_value(self, model_field, value):
        """Resolve what is being *written* -- ``_corrections_in`` runs before the
        write lands, so the record still holds the old numbers."""
        if model_field != "phone_ids":
            return super()._extract_compare_value(model_field, value)
        phone_ids = _ids_in_x2many(value)
        if not phone_ids:
            _debug.logic(
                "cv_phone_not_comparable",
                reason="no_ids_in_the_write",
                applicant=self,
            )
            return NOT_COMPARABLE
        return self.env["phone.number"].browse(phone_ids)[:1].number or NOT_COMPARABLE

    @api.depends("stage_id", "job_id", "extract_state")
    def _compute_extract_can_be_read(self) -> None:
        first_stage_by_job = {}
        for applicant in self:
            job_id = applicant.job_id.id
            if job_id not in first_stage_by_job:
                first_stage_by_job[job_id] = applicant._get_first_recruitment_stage()
            _debug.logic(
                "cv_read_eligibility",
                applicant=applicant,
                stage=applicant.stage_id,
                first_stage=first_stage_by_job[job_id],
                extract_state=applicant.extract_state,
            )
            applicant.extract_can_be_read = applicant.stage_id == first_stage_by_job[
                job_id
            ] and applicant.extract_state in ("none", "failed", "partial")

    def _get_first_recruitment_stage(self):
        self.check_singleton()
        return self.env["hr.recruitment.stage"].search(
            [
                "|",
                ("job_ids", "=", False),
                ("job_ids", "=", self.job_id.id),
                ("fold", "=", False),
            ],
            order="sequence asc",
            limit=1,
        )

    def action_extract_document(self):
        self.check_singleton()
        if not self.extract_can_be_read:
            _debug.logic(
                "cv_read_refused",
                reason="applicant_past_the_first_stage",
                applicant=self,
                stage=self.stage_id,
                extract_state=self.extract_state,
            )
            raise UserError(
                _(
                    "A CV is read while the applicant is still in the first stage. "
                    "Past it somebody has been through this record, and a reading "
                    "would be correcting a person from a document they have read."
                )
            )
        result = self._extract_document()
        if result is None:
            _debug.logic(
                "cv_read_absent", reason="no_extraction_result", applicant=self
            )
            return False
        _debug.lifecycle(
            "cv_read",
            applicant=self,
            satisfied=result.satisfied,
            missing=len(result.missing),
        )
        if result.satisfied:
            message = _("The CV was read in full.")
        else:
            message = _(
                "The CV was read in part. Still missing: %(fields)s",
                fields=", ".join(result.missing) or _("nothing required"),
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "info", "sticky": False},
        }
