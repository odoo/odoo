# -*- coding: utf-8 -*-
"""Report wizard engine shared by every printable Jasper form.

Ported from the Odoo 15 ``dtr.jasper.report`` mixin.  A concrete form (for
example ``invoice.form``) inherits this model, declares its own parameters and
overrides :meth:`get_parameters`; the engine then compiles the ``.jrxml``,
runs JasperStarter against the database and exposes the generated PDF/XLSX.

Differences vs. the legacy implementation:

* JasperStarter is invoked through :mod:`od19_reporting_jasper.jasperpy`
  (direct Java call) instead of a shell string.
* The database connection comes from :class:`od19.jasper.db` instead of a
  role created on the fly.
* ``base64.encodestring`` (removed in Python 3.9) is replaced by
  ``base64.encodebytes``, and the report view toggles with ``invisible``
  instead of the removed ``states`` attribute.
"""
import base64
import logging
import os
import shutil
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.od19_reporting_jasper.jasperpy import JasperPy, JasperPyError

_logger = logging.getLogger(__name__)


class JasperReportEngine(models.TransientModel):
    _name = "od19.jasper.report"
    _description = "Jasper Report Wizard"
    _rec_name = "name"

    # ---------------------------------------------------------------- wizard
    name = fields.Char(string="Report Name", default="Print Form", required=True)
    iso_document_id = fields.Many2one(
        "od19.iso.document",
        string="ISO Document",
        help="เลือกเอกสารควบคุม ISO เพื่อนำเลขทะเบียน (code) มาต่อท้ายชื่อไฟล์ "
        "และพิมพ์ลงในรายงาน; ถ้าไม่เลือกจะไม่แสดงเลขทะเบียน",
    )
    iso_no = fields.Char(
        string="ISO No.",
        compute="_compute_iso_no",
        store=True,
        help="เลขทะเบียน ISO ที่ดึงจากเอกสารควบคุม ISO ที่เลือกไว้",
    )
    name_pdf = fields.Char(string="PDF File Name", compute="_compute_file_name", store=True)
    name_xlsx = fields.Char(string="XLSX File Name", compute="_compute_file_name", store=True)
    jasper_file = fields.Char(
        string="Jasper File",
        help="Absolute path to the compiled .jasper file.",
    )
    state = fields.Selection(
        [("input", "Input"), ("output", "Output")],
        string="State",
        default="input",
        required=True,
    )
    output_pdf = fields.Binary(string="PDF", readonly=True)
    output_xlsx = fields.Binary(string="XLSX", readonly=True)

    # ------------------------------------------------------------- emailing
    partner_ids = fields.Many2many("res.partner", string="Recipients")
    email_template_id = fields.Many2one("mail.template", string="Email Template")
    can_send_email = fields.Boolean(string="Can Send by Email")
    email_subject = fields.Char(string="Email Subject")
    email_document_number = fields.Char(string="Document Number")
    email_to = fields.Char(string="Email To")

    err_msg = fields.Text(string="Error", readonly=True)

    # ------------------------------------------------------------ boundaries
    @api.depends("iso_document_id")
    def _compute_iso_no(self):
        for record in self:
            record.iso_no = record.iso_document_id.code or ""

    @api.depends("name", "iso_no")
    def _compute_file_name(self):
        for record in self:
            base = record.name or "Print Form"
            if record.iso_no:
                base = "%s (%s)" % (base, record.iso_no)
            record.name_pdf = "%s.pdf" % base
            record.name_xlsx = "%s.xlsx" % base

    # ------------------------------------------------------------------ paths
    def get_jasper_file(self, module_report_file=__file__, ext=".jasper", base_name=None):
        """Absolute path of the compiled report shipped in ``<module>/jrxml``.

        ``base_name`` overrides the template name when the JRXML is not named
        after the Python file that declares the report (e.g. ``ar_ap_aging.py``
        ships ``ar_ap_aging_report.jrxml``).
        """
        folder, file_name = os.path.split(os.path.abspath(module_report_file))
        base = base_name or os.path.splitext(file_name)[0]
        return os.path.join(os.path.dirname(folder), "jrxml", base + ext)

    def get_jrxml_file(self):
        path = self.jasper_file or ""
        if path.lower().endswith(".jasper"):
            return path[: -len(".jasper")] + ".jrxml"
        return path

    def check_jasper_file(self):
        self.ensure_one()
        jrxml = self.get_jrxml_file()
        if not jrxml or not os.path.isfile(jrxml):
            raise UserError(
                _("Report template not found: %s") % (jrxml or "-")
            )

    def _auto_compile_if_needed(self):
        """Compile the ``.jrxml`` when the ``.jasper`` is missing or stale."""
        self.check_jasper_file()
        jrxml = self.get_jrxml_file()
        compiled = jrxml[: -len(".jrxml")] + ".jasper"
        if (
            not os.path.isfile(compiled)
            or os.path.getmtime(jrxml) > os.path.getmtime(compiled)
        ):
            try:
                JasperPy().compile(jrxml, compiled)
            except JasperPyError as error:
                _logger.error("Jasper report compilation failed: %s", error)
                raise UserError(
                    _("Unable to compile the report template.\n%s") % error
                )
        if compiled != self.jasper_file:
            self.jasper_file = compiled
        return compiled

    # -------------------------------------------------------------- run-time
    def get_locale(self):
        return "th_TH"

    # ------------------------------------------------- legacy parameter map
    # In Odoo 15 every ``dtr.jasper.report`` subclass rebuilt the same parameter
    # dict by hand.  An audit of the 87 legacy templates shipped under
    # ``odoo15_mods_accounting`` shows a stable shared contract, so the common
    # values are built once here and reused by every ported form:
    #
    #   p_DateFormat 40/87   p_language 35/87   p_locale 33/87
    #   p_Print_By   29/87   p_Where    26/87   ids      10/87
    #   iscopy        9/87
    #
    # ``p_Where`` stays report-specific (each report composes its own filter),
    # and ``p_Path`` / ``p_ISO`` / ``p_EName`` / ``p_ESignature`` come from the
    # legacy report-template configuration, so they are not generalised here.
    LEGACY_DEFAULT_DATE_FORMAT = "dd-MM-yyyy"

    def _legacy_ids_where(self, alias, extra=""):
        """Legacy ``ids`` parameter, e.g. ``where invoice.id in (1, 2, 3)``."""
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        clause = "where %s.id in (%s)" % (alias, ", ".join(str(i) for i in ids))
        return ("%s %s" % (clause, extra)).strip()

    def _legacy_is_copy(self):
        return "%s" % (1 if self.env.context.get("iscopy") else 0)

    def _legacy_locale(self):
        """``BE`` (พ.ศ.) prints Thai dates, ``AD`` prints Gregorian."""
        return "th" if getattr(self, "date_type", "AD") == "BE" else "en"

    def _legacy_print_by(self):
        return self.env.user.name or ""

    def _legacy_filestore_path(self):
        """Absolute filestore folder, used by reports that load signature images.

        Legacy printed ``"{data_dir}/filestore/{dbname}/"``; Odoo 19 exposes the
        same folder through :meth:`ir.attachment._filestore`.
        """
        path = self.env["ir.attachment"]._filestore()
        return path.replace("\\", "/") + "/"

    def get_common_parameters(self):
        """Parameters shared by nearly every legacy printable report."""
        return {
            "p_language": getattr(self, "p_language", "thai"),
            "p_locale": self._legacy_locale(),
            "p_DateFormat": str(
                getattr(self, "date_format", self.LEGACY_DEFAULT_DATE_FORMAT)
            ),
        }

    def get_parameters(self):
        """Jasper parameters, passed to jasperstarter as ``-P key=value``."""
        return {}

    def get_partner_ids_for_send_by_email(self):
        return self.env["res.partner"]

    def _get_db_connection(self):
        return self.env["od19.jasper.db"].get_connection_dict()

    def get_temp_file_path(self):
        tmpdir = tempfile.mkdtemp(prefix="od19_jasper_")
        base = os.path.splitext(os.path.basename(self.name_pdf or "report.pdf"))[0]
        return tmpdir, os.path.join(tmpdir, base or "report")

    def clean_up_temp(self, tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

    def process_jasper_file(self, output_file, format_list=None, db=True):
        self.ensure_one()
        format_list = list(format_list or ("pdf", "xlsx"))
        jasper = JasperPy()
        parameters = {
            "output_file": output_file,
            "format_list": format_list,
            "parameters": self.get_parameters(),
            "locale": self.get_locale(),
            "resource": os.path.dirname(self.jasper_file or ""),
        }
        if db:
            parameters["db_connection"] = self._get_db_connection()
        try:
            jasper.process(self.jasper_file, **parameters)
        except JasperPyError as error:
            _logger.error("Jasper report generation failed: %s", error)
            raise UserError(
                _("Unable to generate the report.\n%s") % error
            )

    def write_file_to_field(self, file_path_prefix):
        self.ensure_one()
        values = {"state": "output", "err_msg": False}
        pdf_path = file_path_prefix + ".pdf"
        xlsx_path = file_path_prefix + ".xlsx"
        if os.path.isfile(pdf_path):
            with open(pdf_path, "rb") as stream:
                values["output_pdf"] = base64.encodebytes(stream.read())
        if os.path.isfile(xlsx_path):
            with open(xlsx_path, "rb") as stream:
                values["output_xlsx"] = base64.encodebytes(stream.read())
        self.write(values)

    # -------------------------------------------------------------- lifecycle
    def _action_reopen_wizard(self):
        """Return the action that keeps the wizard dialog on screen.

        Odoo 19 treats a falsy return value of an ``object`` button as
        ``ir.actions.act_window_close`` (see ``action_service.js``), so a
        ``return None`` closes the dialog before the user can see the
        generated file.  Returning an ``act_window`` action whose
        ``target`` is ``new`` makes the action service swap the current
        dialog for this very record, now rendered in its ``output`` state.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self._description or self.name or _("Print Form"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context),
        }

    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        """Generate the report and flip the wizard to its output state."""
        self.ensure_one()
        self._auto_compile_if_needed()

        partner_ids = self.get_partner_ids_for_send_by_email()
        values = {}
        if report_name:
            values["name"] = report_name
        if partner_ids:
            values["partner_ids"] = [(6, 0, partner_ids.ids)]
        if email_subject:
            values["email_subject"] = email_subject
        if email_document_number:
            values["email_document_number"] = email_document_number
        if values:
            self.write(values)

        tmpdir, tmp_prefix = self.get_temp_file_path()
        try:
            self.process_jasper_file(tmp_prefix)
            self.write_file_to_field(tmp_prefix)
        finally:
            self.clean_up_temp(tmpdir)

        if not self.output_pdf:
            raise UserError(_("The report engine did not produce any file."))
        return self._action_reopen_wizard()

    def reprint(self):
        """Go back to the input state, keeping the entered parameters."""
        self.ensure_one()
        self.write(
            {
                "state": "input",
                "output_pdf": False,
                "output_xlsx": False,
                "err_msg": False,
            }
        )
        return self._action_reopen_wizard()

    def action_send_email(self):
        self.ensure_one()
        attachment = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_field", "=", "output_pdf"),
                ("res_id", "=", self.id),
            ],
            limit=1,
        )
        if attachment and self.email_subject:
            attachment.name = self.email_subject
        return {
            "type": "ir.actions.act_window",
            "name": _("Send by Email"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "view_id": self.env.ref("mail.email_compose_message_wizard_form").id,
            "target": "new",
            "context": dict(
                self.env.context,
                active_model=self._name,
                active_id=self.id,
                active_ids=self.ids,
                default_model=self._name,
                default_res_ids=self.ids,
                default_use_template=bool(self.email_template_id),
                default_template_id=self.email_template_id.id,
                default_composition_mode="comment",
                default_subject=self.email_subject,
                default_attachment_ids=[(6, 0, attachment.ids)],
                default_partner_ids=[(6, 0, self.partner_ids.ids)],
                force_email=True,
            ),
        }

    @api.model
    def get_file_name(self, ids, model_name, default_file_name="DownloadFile"):
        """Document reference used as the report title."""
        if not ids:
            return default_file_name
        if len(ids) == 1:
            return (
                self.env[model_name].browse(ids[0]).display_name or default_file_name
            )
        return default_file_name
