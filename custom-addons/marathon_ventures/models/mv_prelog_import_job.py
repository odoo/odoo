# -*- coding: utf-8 -*-

import base64
import csv
import hashlib
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.prelog_import.config_loader import slugify_program_name
from ..services.prelog_import.engine import PrelogImportEngine

_logger = logging.getLogger(__name__)


class MvPrelogImportJob(models.Model):
    _name = "mv.prelog_import_job"
    _description = "Prelog Import Job"
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Job Name",
        default=lambda self: self.env["ir.sequence"].next_by_code("mv.prelog_import_job.name") or "New",
        copy=False,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="queued",
        required=True,
        index=True,
    )
    upload_file = fields.Binary(string="Upload", required=True, attachment=True)
    upload_filename = fields.Char(string="Filename", required=True)
    file_checksum = fields.Char(string="File Checksum", required=True, index=True, copy=False)
    program_id = fields.Many2one("mv.programs", string="Program", required=True, ondelete="restrict", index=True)
    import_week = fields.Date(string="Import Week", required=True, index=True)
    prelog_version = fields.Integer(string="Prelog Version", required=True)
    replace_existing = fields.Boolean(string="Replace Existing Version")
    submitted_by_id = fields.Many2one(
        "res.users",
        string="Submitted By",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        index=True,
    )
    started_at = fields.Datetime(string="Started At", readonly=True)
    finished_at = fields.Datetime(string="Finished At", readonly=True)
    failure_message = fields.Text(string="Failure Message", readonly=True)
    summary_message = fields.Text(string="Summary", readonly=True)
    existing_prelogs_deleted_count = fields.Integer(string="Deleted Existing Prelogs", readonly=True)
    total_row_count = fields.Integer(string="Total Rows", readonly=True)
    matched_count = fields.Integer(string="Matched Rows", readonly=True)
    unmatched_count = fields.Integer(string="Unmatched Rows", readonly=True)
    error_count = fields.Integer(string="Error Rows", readonly=True)
    combined_issue_count = fields.Integer(string="Combined Issue Count", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)
    total_rate_amount = fields.Monetary(string="Total Upload Amount", currency_field="currency_id", readonly=True)
    matched_rate_amount = fields.Monetary(string="Matched Amount", currency_field="currency_id", readonly=True)
    unmatched_rate_amount = fields.Monetary(string="Unmatched Amount", currency_field="currency_id", readonly=True)
    success_attachment_id = fields.Many2one("ir.attachment", string="Success CSV", readonly=True, ondelete="set null")
    error_attachment_id = fields.Many2one("ir.attachment", string="Errors CSV", readonly=True, ondelete="set null")
    notification_email = fields.Char(string="Notification Email", readonly=True)
    notification_sent = fields.Boolean(string="Notification Sent", readonly=True)
    notification_failure = fields.Text(string="Notification Failure", readonly=True)
    prelog_ids = fields.One2many("mv.prelog_data", "import_job", string="Prelog Rows")

    @api.model
    def create_from_wizard(self, *, program, upload_file, upload_filename, import_week, prelog_version, replace_existing):
        user_email = (self.env.user.partner_id.email or "").strip()
        if not user_email:
            raise UserError(_("Your user account must have an email address before starting a Prelog upload."))

        file_checksum = hashlib.sha256(base64.b64decode(upload_file or b"")).hexdigest()
        duplicate_job = self.search(
            [
                ("state", "in", ["queued", "running"]),
                ("submitted_by_id", "=", self.env.user.id),
                ("program_id", "=", program.id),
                ("import_week", "=", import_week),
                ("prelog_version", "=", prelog_version),
                ("file_checksum", "=", file_checksum),
            ],
            limit=1,
            order="id desc",
        )
        if duplicate_job:
            return duplicate_job, False

        job = self.create(
            {
                "upload_file": upload_file,
                "upload_filename": upload_filename,
                "file_checksum": file_checksum,
                "program_id": program.id,
                "import_week": import_week,
                "prelog_version": prelog_version,
                "replace_existing": replace_existing,
                "submitted_by_id": self.env.user.id,
                "notification_email": user_email,
            }
        )
        return job, True

    @api.model
    def _cron_process_prelog_import_jobs(self):
        jobs = self.search([("state", "=", "queued")], order="create_date asc, id asc", limit=1)
        for job in jobs:
            job._run_job()

    def _run_job(self):
        self.ensure_one()
        if self.state not in ("queued", "running"):
            return

        self.write(
            {
                "state": "running",
                "started_at": fields.Datetime.now(),
                "finished_at": False,
                "failure_message": False,
                "summary_message": False,
                "notification_failure": False,
                "notification_sent": False,
            }
        )

        try:
            summary = self._process_rows()
            email_sent, email_failure = self._send_completion_email()
            update_vals = {
                "state": "completed",
                "finished_at": fields.Datetime.now(),
                "summary_message": self._build_summary_text(),
                "notification_sent": email_sent,
                "notification_failure": email_failure or False,
            }
            update_vals.update(summary)
            self.write(update_vals)
        except Exception as exc:
            _logger.exception("Prelog import job %s failed.", self.id)
            email_sent, email_failure = self._send_failure_email(str(exc))
            self.write(
                {
                    "state": "failed",
                    "finished_at": fields.Datetime.now(),
                    "failure_message": str(exc),
                    "summary_message": self._build_summary_text(),
                    "notification_sent": email_sent,
                    "notification_failure": email_failure or False,
                }
            )

    def _process_rows(self):
        self.ensure_one()
        engine = PrelogImportEngine(
            self.env,
            program=self.program_id,
            upload_file=self.upload_file,
            upload_filename=self.upload_filename,
        )
        rows, detected_week = engine.extract_rows_and_week()
        if detected_week != self.import_week:
            self.import_week = detected_week

        existing_prelogs_deleted_count = 0
        if self.replace_existing:
            existing_prelogs = self.env["mv.prelog_data"].search(
                [
                    ("version", "=", self.prelog_version),
                    "|",
                    "&",
                    ("import_program", "=", self.program_id.id),
                    ("import_week_value", "=", self.import_week),
                    "&",
                    ("schedule.deal_parent.program", "=", self.program_id.id),
                    ("schedule.week", "=", self.import_week),
                ]
            )
            existing_prelogs_deleted_count = len(existing_prelogs)
            if existing_prelogs:
                existing_prelogs.unlink()

        success_rows = []
        error_rows = []
        matched_count = 0
        unmatched_count = 0
        error_count = 0
        total_rate_amount = 0.0
        matched_rate_amount = 0.0
        unmatched_rate_amount = 0.0

        for row_index, row in enumerate(rows, start=engine._first_data_row_number()):
            vals = False
            rate_added = False
            try:
                vals = engine.build_row_vals(row, self.import_week, self.prelog_version, row_index)
                vals["import_job"] = self.id
                rate_value = float(vals.get("rate") or 0.0)
                total_rate_amount += rate_value
                rate_added = True
                with self.env.cr.savepoint():
                    prelog = self.env["mv.prelog_data"].create(vals)

                if vals["import_match_status"] == "matched":
                    matched_count += 1
                    matched_rate_amount += rate_value
                    success_rows.append(self._build_success_csv_row(engine, prelog, row, vals))
                else:
                    unmatched_count += 1
                    unmatched_rate_amount += rate_value
                    error_rows.append(self._build_error_csv_row(engine, row, vals, status="no-match"))
            except Exception as exc:
                _logger.exception("Prelog import job %s row %s failed.", self.id, row_index)
                error_count += 1
                error_rows.append(self._build_error_csv_row(engine, row, vals, status="error", detail=str(exc)))
                if not rate_added:
                    rate_value = vals.get("rate") if vals else row.get("rate")
                    try:
                        total_rate_amount += float(rate_value or 0.0)
                    except (TypeError, ValueError):
                        pass

        attachments = self._create_result_attachments(
            engine=engine,
            success_rows=success_rows,
            error_rows=error_rows,
        )

        combined_issue_count = unmatched_count + error_count
        summary = {
            "existing_prelogs_deleted_count": existing_prelogs_deleted_count,
            "total_row_count": len(rows),
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
            "error_count": error_count,
            "combined_issue_count": combined_issue_count,
            "total_rate_amount": total_rate_amount,
            "matched_rate_amount": matched_rate_amount,
            "unmatched_rate_amount": unmatched_rate_amount,
            "success_attachment_id": attachments["success_attachment_id"],
            "error_attachment_id": attachments["error_attachment_id"],
        }
        self.write(summary)
        return summary

    def _create_result_attachments(self, *, engine, success_rows, error_rows):
        self.ensure_one()
        attachment_vals = {}
        success_name = self._attachment_filename("uploaded-prelogs")
        error_name = self._attachment_filename("errors")

        success_csv = self._csv_bytes(
            rows=success_rows,
            fieldnames=["Prelog Name", "Schedule"] + engine.export_field_names(),
        )
        error_csv = self._csv_bytes(
            rows=error_rows,
            fieldnames=["Status", "Detail"] + engine.export_field_names(),
        )

        success_attachment = self.env["ir.attachment"].create(
            {
                "name": success_name,
                "datas": base64.b64encode(success_csv),
                "mimetype": "text/csv",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        error_attachment = self.env["ir.attachment"].create(
            {
                "name": error_name,
                "datas": base64.b64encode(error_csv),
                "mimetype": "text/csv",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        attachment_vals["success_attachment_id"] = success_attachment.id
        attachment_vals["error_attachment_id"] = error_attachment.id
        return attachment_vals

    def _send_completion_email(self):
        self.ensure_one()
        email_to = (self.notification_email or "").strip()
        if not email_to:
            return False, _("No notification email address was available for this job.")

        attachments = [attachment.id for attachment in (self.success_attachment_id, self.error_attachment_id) if attachment]
        mail = self.env["mail.mail"].create(
            {
                "subject": _(
                    "Prelog Upload Complete %(issues)s errors, %(matched)s prelogs created for %(filename)s"
                )
                % {
                    "issues": self.combined_issue_count,
                    "matched": self.matched_count,
                    "filename": self.upload_filename,
                },
                "email_to": email_to,
                "email_from": self.env.company.email_formatted or self.env.user.email_formatted or False,
                "body_html": self._build_email_body_html(),
                "attachment_ids": [(6, 0, attachments)],
            }
        )
        try:
            mail.send()
        except Exception as exc:
            _logger.exception("Prelog import job %s email send failed.", self.id)
            return False, str(exc)
        return True, False

    def _send_failure_email(self, failure_message):
        self.ensure_one()
        email_to = (self.notification_email or "").strip()
        if not email_to:
            return False, _("No notification email address was available for this job.")

        mail = self.env["mail.mail"].create(
            {
                "subject": _("Prelog Upload Failed for %s") % self.upload_filename,
                "email_to": email_to,
                "email_from": self.env.company.email_formatted or self.env.user.email_formatted or False,
                "body_html": """
                    <p>Your prelog upload of file <strong>{filename}</strong> failed.</p>
                    <p>Error: {message}</p>
                """.format(
                    filename=self.upload_filename,
                    message=failure_message,
                ),
            }
        )
        try:
            mail.send()
        except Exception as exc:
            _logger.exception("Prelog import job %s failure email send failed.", self.id)
            return False, str(exc)
        return True, False

    def _build_email_body_html(self):
        self.ensure_one()
        return """
            <p>Your prelog upload of file <strong>{filename}</strong> completed.</p>
            <p>{matched} rows were successfully uploaded as prelog records to Odoo and matched to their schedules (see attached uploaded-prelogs.csv).</p>
            <p>{unmatched} rows were uploaded as prelog records to Odoo but did not match a schedule (see attached errors.csv).</p>
            <p>{errors} rows were not processed due to errors (see attached errors.csv).</p>
            <p>Total upload amount: <strong>{total_amount}</strong></p>
            <p>Matched amount: <strong>{matched_amount}</strong></p>
            <p>Unmatched amount: <strong>{unmatched_amount}</strong></p>
        """.format(
            filename=self.upload_filename,
            matched=self.matched_count,
            unmatched=self.unmatched_count,
            errors=self.error_count,
            total_amount=self._format_amount(self.total_rate_amount),
            matched_amount=self._format_amount(self.matched_rate_amount),
            unmatched_amount=self._format_amount(self.unmatched_rate_amount),
        )

    def _build_summary_text(self):
        self.ensure_one()
        return _(
            "Matched: %(matched)s, Unmatched: %(unmatched)s, Errors: %(errors)s, Total Amount: %(amount)s"
        ) % {
            "matched": self.matched_count,
            "unmatched": self.unmatched_count,
            "errors": self.error_count,
            "amount": self._format_amount(self.total_rate_amount),
        }

    def _attachment_filename(self, prefix):
        self.ensure_one()
        network_slug = slugify_program_name(self.program_id.display_name)
        return f"{prefix}-{network_slug}-{self.import_week}-v{self.prelog_version}.csv"

    @staticmethod
    def _format_amount(amount):
        return "${:,.2f}".format(float(amount or 0.0))

    @staticmethod
    def _csv_bytes(*, rows, fieldnames):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8")

    def _build_success_csv_row(self, engine, prelog, raw_row, vals):
        row = {
            "Prelog Name": prelog.name or False,
            "Schedule": prelog.schedule.display_name if prelog.schedule else False,
        }
        for field_name in engine.export_field_names():
            source_value = vals.get(field_name)
            if source_value in (None, False, ""):
                source_value = raw_row.get(field_name)
            row[field_name] = self._serialize_csv_value(source_value)
        return row

    def _build_error_csv_row(self, engine, raw_row, vals, *, status, detail=False):
        row = {
            "Status": status,
            "Detail": detail or (vals or {}).get("import_match_detail") or False,
        }
        for field_name in engine.export_field_names():
            source_value = (vals or {}).get(field_name)
            if source_value in (None, False, ""):
                source_value = raw_row.get(field_name)
            row[field_name] = self._serialize_csv_value(source_value)
        return row

    @staticmethod
    def _serialize_csv_value(value):
        if value in (None, False):
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value
