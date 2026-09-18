import io
import logging
from ast import literal_eval
from collections.abc import Callable
from typing import Any, Self

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.barcode import (
    createBarcodeDrawing,
    get_barcode_font,
    is_barcode_encoding_valid,
)
from odoo.libs.debug_log import DebugLog
from odoo.tools import is_html_empty
from odoo.tools.pdf import BrandedFileWriter, PdfReader, PdfReadError
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("1", "true", "yes", "on"):
            return True
        if token in ("0", "false", "no", "off", ""):
            return False
    return default


class IrActionsReport(models.Model):
    _name = "ir.actions.report"
    _description = "Report Action"
    _inherit = ["ir.actions.actions"]
    _table = "ir_act_report_xml"

    model = fields.Char(
        string="Model Name",
        required=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        compute="_compute_model_id",
        search="_search_model_id",
    )

    report_type = fields.Selection(
        selection=[
            ("qweb-html", "HTML"),
            ("qweb-pdf", "PDF"),
            ("qweb-text", "Text"),
        ],
        default="qweb-pdf",
        required=True,
        help="The type of the report that will be rendered, each one having its own"
        " rendering method. HTML means the report will be opened directly in your"
        " browser. PDF means the report will be rendered using WeasyPrint and"
        " downloaded by the user.",
    )
    report_name = fields.Char(
        string="Template Name",
        index=True,
        required=True,
    )
    report_file = fields.Char(
        store=True,
        readonly=False,
        required=False,
        help="The path to the main report file (depending on Report Type) or empty if the content is in another field",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="res_groups_report_rel",
        column1="uid",
        column2="gid",
        string="Groups",
        help="Users outside these groups do not see the report in menus and "
        "print toolbars. Printing itself is bounded by read access to the "
        "records being rendered, not by these groups.",
    )
    multi = fields.Boolean(
        string="On Multiple Doc.",
        help="If set to true, the action will not be displayed on the right toolbar of a form view.",
    )

    paperformat_id = fields.Many2one(
        comodel_name="report.paperformat",
        string="Paper Format",
        index="btree_not_null",
    )
    print_report_name = fields.Char(
        string="Printed Report Name",
        translate=True,
        help="This is the filename of the report going to download. Keep empty to not change the report filename. You can use a python expression with the 'object' and 'time' variables.",
    )
    attachment_use = fields.Boolean(
        string="Reload from Attachment",
        help="If enabled, then the second time the user prints with same attachment name, it returns the previous report.",
    )
    attachment = fields.Char(
        string="Save as Attachment Prefix",
        help="This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.",
    )
    domain = fields.Char(
        string="Filter domain",
        help="If set, the action will only appear on records that matches the domain.",
    )

    _BINDING_TYPE = "report"

    @api.depends("model")
    def _compute_model_id(self) -> None:
        for action in self:
            action.model_id = self.env["ir.model"]._get(action.model).id

    def _search_model_id(self, operator: str, value: Any) -> Any:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        model_records = self.env["ir.model"]
        if isinstance(value, str):
            model_records = model_records.search(
                Domain("display_name", operator, value)
            )
        elif isinstance(value, Domain):
            model_records = model_records.search(value)
        elif operator == "any!":
            model_records = model_records.sudo().search(Domain("id", operator, value))
        elif operator == "any" or isinstance(value, int):
            model_records = model_records.search(Domain("id", operator, value))
        elif operator == "in":
            model_records = model_records.search(
                Domain.OR(
                    Domain(
                        "id" if isinstance(v, int) else "display_name",
                        operator,
                        v,
                    )
                    for v in value
                    if v
                )
            )
        else:
            _debug.logic("model_search_unsupported", operator=operator)
            return NotImplemented
        _debug.logic("model_search", operator=operator, models=len(model_records))
        return Domain("model", "in", model_records.mapped("model"))

    def _get_field_target_model(self) -> str:
        return "model"

    def _get_field_groups(self) -> str:
        return "group_ids"

    def _get_fields_binding_extra(self) -> tuple[str, ...]:
        return ("group_ids", "domain")

    def _get_fields_readable(self) -> frozenset[str]:
        return super()._get_fields_readable() | {
            "report_name",
            "report_type",
            "domain",
        }

    def _get_keys_client_only(self) -> frozenset[str]:
        return super()._get_keys_client_only() | {
            "target",
            "context",
            "data",
            "close_on_report_download",
        }

    def action_view_qweb_views(self) -> dict[str, Any] | bool:
        self.check_singleton()
        action_ref = self.env.ref("base.action_ui_view", raise_if_not_found=False)
        if not action_ref or len(self.report_name.split(".")) < 2:
            _debug.logic(
                "qweb_views_unavailable",
                report=self.id,
                reason="no_action" if not action_ref else "unqualified_name",
            )
            return False
        action_data = action_ref.read()[0]
        action_data["domain"] = [
            ("name", "ilike", self.report_name.split(".")[1]),
            ("type", "=", "qweb"),
        ]
        return action_data

    def _get_attachment_filenames(self, records: Any) -> dict[int, Any]:
        self.check_singleton()
        if not self.attachment:
            return dict.fromkeys(records.ids, "")
        with _debug.perf(
            "attachment_filenames", report=self.id, records=len(records)
        ) as span:
            filenames = {
                record.id: safe_eval(self.attachment, {"object": record, "time": time})
                or ""
                for record in records
            }
            span.set(named=sum(1 for name in filenames.values() if name))
        return filenames

    def _get_attachments(
        self, records: Any, filenames: dict[int, Any] | None = None
    ) -> dict[int, Any]:
        self.check_singleton()
        if filenames is None:
            filenames = self._get_attachment_filenames(records)
        names_by_id = {res_id: name for res_id, name in filenames.items() if name}
        if not names_by_id:
            return {}
        attachments = self.env["ir.attachment"].search(
            [
                ("name", "in", list(set(names_by_id.values()))),
                ("res_model", "=", self.model),
                ("res_id", "in", list(names_by_id)),
            ]
        )
        result: dict[int, Any] = {}
        for attachment in attachments:
            res_id = attachment.res_id
            if res_id not in result and attachment.name == names_by_id.get(res_id):
                result[res_id] = attachment
        _debug.logic(
            "saved_attachments_looked_up",
            report=self.id,
            records=len(records),
            named=len(names_by_id),
            found=len(result),
        )
        return result

    def get_paperformat(self) -> Any:
        if self.paperformat_id:
            _debug.logic("paperformat", report=self.id, source="report")
            return self.paperformat_id
        if self.env.company.paperformat_id:
            _debug.logic("paperformat", report=self.id, source="company")
            return self.env.company.paperformat_id
        _debug.logic("paperformat", report=self.id, source="default")
        return self.env.ref("base.paperformat_euro", raise_if_not_found=False)

    def get_paperformat_by_xmlid(self, xml_id: str) -> Any:
        return (
            self.env.ref(xml_id).get_paperformat()
            if xml_id
            else self.env.company.paperformat_id
        )

    @api.model
    def _get_report_from_name(self, report_name: str) -> Self:
        if not report_name:
            return self.env["ir.actions.report"]
        try:
            return self._get_report(report_name)
        except ValueError:
            _debug.logic("report_from_name_missing", name=report_name)
            return self.env["ir.actions.report"]

    @api.model
    def _get_report(self, report_ref: int | str | Any) -> Self:
        ReportSudo = self.env["ir.actions.report"].sudo()
        if isinstance(report_ref, bool):
            _debug.logic("report_ref_refused", reason="bool")
            raise ValueError(
                f"Fetching report {report_ref!r}: invalid report reference"
            )
        if isinstance(report_ref, int):
            _debug.logic("report_resolved", ref=report_ref, by="id")
            report = ReportSudo.browse(report_ref)
        elif isinstance(report_ref, models.Model):
            if report_ref._name != self._name:
                _debug.logic(
                    "report_ref_refused", reason="wrong_model", model=report_ref._name
                )
                msg = f"Expected report of type {self._name}, got {report_ref._name}"
                raise ValueError(msg)
            _debug.logic("report_resolved", ref=report_ref.id, by="record")
            report = report_ref.sudo()
        else:
            report = ReportSudo.search([("report_name", "=", report_ref)], limit=1)
            _debug.logic(
                "report_resolved",
                ref=report_ref,
                by="report_name" if report else "xmlid",
            )
            if not report:
                report = self.env.ref(report_ref, raise_if_not_found=False)
                if not report:
                    _debug.logic(
                        "report_ref_refused", ref=report_ref, reason="not_found"
                    )
                    raise ValueError(
                        f"Fetching report {report_ref!r}: report not found"
                    )
                if report._name != "ir.actions.report":
                    _debug.logic(
                        "report_ref_refused",
                        ref=report_ref,
                        reason="wrong_model",
                        model=report._name,
                    )
                    raise ValueError(
                        f"Fetching report {report_ref!r}: type {report._name}, expected ir.actions.report"
                    )
                report = report.sudo()
        return report

    @api.model
    def prepare_barcode(self, barcode_type: str, value: str, **kwargs: Any) -> bytes:
        defaults = {
            "width": (600, int),
            "height": (100, int),
            "humanreadable": (False, lambda x: _coerce_bool(x, False)),
            "quiet": (True, lambda x: _coerce_bool(x, True)),
            "mask": (None, lambda x: x),
            "barBorder": (4, int),
            "barLevel": (
                "L",
                lambda x: (x in ("L", "M", "Q", "H") and x) or "L",
            ),
        }
        kwargs = {
            k: validator(kwargs.get(k, v)) for k, (v, validator) in defaults.items()
        }
        kwargs["humanReadable"] = kwargs.pop("humanreadable")
        if kwargs["humanReadable"]:
            kwargs["fontName"] = get_barcode_font()

        if (
            kwargs["width"] * kwargs["height"] > 1200000
            or max(kwargs["width"], kwargs["height"]) > 10000
        ):
            _debug.logic(
                "barcode_refused",
                type=barcode_type,
                width=kwargs["width"],
                height=kwargs["height"],
                reason="too_large",
            )
            msg = "Barcode too large"
            raise ValueError(msg)
        requested_type = barcode_type

        if barcode_type == "UPCA" and len(value) in (11, 12, 13):
            barcode_type = "EAN13"
            if len(value) in (11, 12):
                value = f"0{value}"
        elif barcode_type == "auto":
            symbology_guess = {8: "EAN8", 13: "EAN13"}
            barcode_type = symbology_guess.get(len(value), "Code128")
        elif barcode_type == "QR":
            if not kwargs["quiet"]:
                kwargs["barBorder"] = 0

        if barcode_type in ("EAN8", "EAN13") and not is_barcode_encoding_valid(
            value, barcode_type
        ):
            barcode_type = "Code128"

        mask_name = kwargs.pop("mask")
        _debug.logic(
            "barcode_type_resolved",
            requested=requested_type,
            resolved=barcode_type,
            length=len(value),
            mask=mask_name,
        )
        try:
            barcode = createBarcodeDrawing(
                barcode_type, value=value, format="png", **kwargs
            )
        except ValueError, AttributeError:
            if barcode_type in ("Code128", "QR"):
                _debug.logic("barcode_refused", type=barcode_type, reason="unencodable")
                msg = f"Cannot convert into {barcode_type} barcode."
                raise ValueError(msg) from None
            _debug.logic("barcode_fallback", requested=barcode_type, resolved="Code128")
            _logger.warning(
                "Cannot draw a %s barcode, falling back to Code128.",
                barcode_type,
                exc_info=True,
            )
            barcode_type = "Code128"
            barcode = createBarcodeDrawing(
                barcode_type, value=value, format="png", **kwargs
            )
        else:
            if mask_name:
                available_masks = self._get_barcode_masks_available()
                mask_to_apply = available_masks.get(mask_name)
                if mask_to_apply:
                    try:
                        mask_to_apply(kwargs["width"], kwargs["height"], barcode)
                    except ValueError, AttributeError:
                        _debug.logic("barcode_mask_failed", mask=mask_name)
                        _logger.warning(
                            "Cannot apply barcode mask %r, returning the "
                            "unmasked %s barcode.",
                            mask_name,
                            barcode_type,
                            exc_info=True,
                        )
        return barcode.asString("png")

    @api.model
    def _get_barcode_masks_available(self) -> dict[str, Callable]:
        return {}

    def _render_template(
        self, template: str, values: dict[str, Any] | None = None
    ) -> bytes:
        user = self.env.user
        view_obj = self.env["ir.ui.view"].with_context(inherit_branding=False)
        values = {
            **(values or {}),
            "time": time,
            "context_timestamp": lambda t: fields.Datetime.context_timestamp(
                self.with_context(tz=user.tz), t
            ),
            "user": user,
            "res_company": self.env.company,
            "web_base_url": self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", default=""),
        }
        with _debug.perf("render_template", cr=self.env.cr, template=template):
            return view_obj._render_template(template, values).encode()

    def _prepare_merge_pdfs_error(
        self,
        error: Exception | None = None,
        error_stream: io.BytesIO | None = None,
    ) -> UserError:
        if error is not None:
            _logger.warning("Unmergeable PDF stream: %s", error, exc_info=error)
        return UserError(_("Odoo is unable to merge the generated PDFs."))

    @api.model
    def _merge_pdfs(
        self,
        streams: list[io.BytesIO],
        on_stream_error: Callable | None = None,
    ) -> io.BytesIO:
        if on_stream_error is None:
            on_stream_error = self._prepare_merge_pdfs_error
        writer = BrandedFileWriter()
        failed = 0
        with _debug.perf("merge_pdfs", streams=len(streams)) as span:
            for stream in streams:
                try:
                    reader = PdfReader(stream)
                    writer.append_pages_from_reader(reader)
                except (
                    PdfReadError,
                    TypeError,
                    NotImplementedError,
                    ValueError,
                ) as e:
                    failed += 1
                    to_raise = on_stream_error(error=e, error_stream=stream)
                    if to_raise is not None:
                        _debug.logic("merge_pdfs_refused", error=type(e).__name__)
                        raise to_raise from e
            result_stream = io.BytesIO()
            try:
                writer.write(result_stream)
            except PdfReadError:
                _debug.logic("merge_pdfs_refused", stage="write")
                raise self._prepare_merge_pdfs_error() from None
            span.set(tolerated=failed, bytes=result_stream.getbuffer().nbytes)
        return result_stream

    @api.model
    def _normalize_render_args(
        self,
        res_ids: list[int] | int | None,
        data: dict[str, Any] | None,
        report_type: str,
    ) -> tuple[list[int] | None, dict[str, Any]]:
        data = dict(data) if data else {}
        data.setdefault("report_type", report_type)
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        return res_ids, data

    @api.model
    def _render_qweb_text(
        self,
        report_ref: int | str | Any,
        docids: list[int] | int | None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        docids, data = self._normalize_render_args(docids, data, "text")
        report = self._get_report(report_ref)
        data = self._prepare_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), "text"

    @api.model
    def _render_qweb_html(
        self,
        report_ref: int | str | Any,
        docids: list[int] | int | None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        docids, data = self._normalize_render_args(docids, data, "html")
        report = self._get_report(report_ref)
        data = self._prepare_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), "html"

    def _get_rendering_context_model(self, report: Self) -> Any | None:
        report_model_name = f"report.{report.report_name}"
        return self.env.get(report_model_name)

    def _prepare_rendering_context(
        self, report: Self, docids: list[int] | None, data: dict[str, Any]
    ) -> dict[str, Any]:
        report_model = self._get_rendering_context_model(report)

        data = (data and dict(data)) or {}
        _debug.pipeline(
            "rendering_context",
            report=report.report_name,
            records=len(docids or ()),
            custom_model=report_model is not None,
        )

        if report_model is not None:
            with _debug.perf(
                "report_values", cr=self.env.cr, report=report.report_name
            ):
                data.update(report_model._get_report_values(docids, data=data))
        else:
            docs = self.env[report.model].browse(docids)
            docs.check_access("read")
            data.update(
                {
                    "doc_ids": docids,
                    "doc_model": report.model,
                    "docs": docs,
                }
            )
        data["is_html_empty"] = is_html_empty
        return data

    @api.model
    def _render(
        self,
        report_ref: int | str | Any,
        res_ids: list[int] | None,
        data: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        report = self._get_report(report_ref)
        report_type = report.report_type.lower().replace("-", "_")
        render_func = getattr(self, "_render_" + report_type, None)
        if not render_func:
            _debug.logic("render_refused", report=report.report_name, type=report_type)
            raise UserError(
                _(
                    "Unknown report type %(type)s for report %(report)s.",
                    type=report.report_type,
                    report=report.report_name,
                )
            )
        with _debug.perf(
            "render",
            cr=self.env.cr,
            report=report.report_name,
            type=report_type,
            records=len(res_ids or ()),
        ):
            return render_func(report, res_ids, data=data)

    def report_action(
        self,
        docids: Any,
        data: dict[str, Any] | None = None,
        config: bool = True,
    ) -> dict[str, Any]:
        context = self.env.context
        if docids:
            if isinstance(docids, models.Model):
                active_ids = docids.ids
            elif isinstance(docids, int):
                active_ids = [docids]
            else:
                active_ids = list(docids)
            context = dict(self.env.context, active_ids=active_ids)
        _debug.pipeline(
            "report_action",
            report=self.report_name,
            type=self.report_type,
            records=len(context.get("active_ids") or ()),
            configured=config,
        )

        return {
            "context": context,
            "data": data,
            "type": "ir.actions.report",
            "report_name": self.report_name,
            "report_type": self.report_type,
            "report_file": self.report_file,
            "name": self.name,
        }

    def get_valid_action_reports(self, model: str, record_ids: list[int]) -> list[int]:
        records = self.env[model].browse(record_ids)
        actions_with_domain = self.filtered("domain")
        valid_action_report_ids = (self - actions_with_domain).ids
        for action in actions_with_domain:
            try:
                domain = literal_eval(action.domain)
            except ValueError, SyntaxError:
                _logger.warning(
                    "Report action %s (id %s) has a malformed domain %r; "
                    "showing the action unconditionally.",
                    action.report_name,
                    action.id,
                    action.domain,
                    exc_info=True,
                )
                _debug.logic("report_domain_malformed", report=action.id)
                valid_action_report_ids.append(action.id)
                continue
            if records.filtered_domain(domain):
                valid_action_report_ids.append(action.id)
        _debug.logic(
            "valid_action_reports",
            model=model,
            records=len(record_ids),
            reports=len(self),
            with_domain=len(actions_with_domain),
            valid=len(valid_action_report_ids),
        )
        return valid_action_report_ids

    @api.model
    def _migrate_attachments_to_local(self, attachments: Any) -> Any:
        remote = 0
        failed = 0
        for attachment in attachments:
            if attachment._is_remote_source():
                remote += 1
                try:
                    attachment._migrate_remote_to_local()
                except (
                    ValidationError,
                    requests.exceptions.RequestException,
                ) as e:
                    failed += 1
                    _logger.error(
                        "Failed to migrate attachment %s to local: %s",
                        attachment.id,
                        e,
                    )
        _debug.lifecycle(
            "attachments_migrated", total=len(attachments), remote=remote, failed=failed
        )
        return attachments.filtered(lambda a: not a._is_remote_source())
