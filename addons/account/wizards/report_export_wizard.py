import base64
import json
import types
from urllib.parse import parse_qs, urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class Account_ReportsExportWizard(models.TransientModel):
    """Export an accounting report in one or more formats as attachments."""

    _name = "account_reports.export.wizard"
    _description = "Export wizard for accounting's reports"

    export_format_ids = fields.Many2many(
        comodel_name="account_reports.export.wizard.format",
        relation="dms_acc_rep_export_wizard_format_rel",
        string="Export to",
    )
    report_id = fields.Many2one(
        comodel_name="account.report",
        string="Parent Report Id",
        required=True,
    )
    doc_name = fields.Char(
        string="Documents Name",
        help="Name to give to the generated documents.",
    )

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard.doc_name = wizard.report_id.name

            # We create one export format object per available export type of the report,
            # with the right generation function associated to it.
            # This is done so to allow selecting them as Many2many tags in the wizard.
            for button_dict in self.env.context.get(
                "account_report_generation_options", {}
            ).get("buttons", []):
                if button_dict.get("file_export_type"):
                    self.env["account_reports.export.wizard.format"].create(
                        {
                            "name": button_dict["file_export_type"],
                            "fun_to_call": button_dict["action"],
                            "fun_param": button_dict.get("action_param"),
                            "export_wizard_id": wizard.id,
                        }
                    )
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "export_formats_created",
                wizards=wizards,
                formats_per_wizard=sum(
                    1
                    for button_dict in self.env.context.get(
                        "account_report_generation_options", {}
                    ).get("buttons", [])
                    if button_dict.get("file_export_type")
                ),
            )
        return wizards

    def export_report(self):
        self.check_singleton()
        created_attachments = self.env["ir.attachment"]
        for vals in self._get_attachments_to_save():
            created_attachments |= self.env["ir.attachment"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "name": _("Generated Documents"),
            "view_mode": "kanban,form",
            "res_model": "ir.attachment",
            "domain": [("id", "in", created_attachments.ids)],
        }

    def _get_attachments_to_save(self):
        self.check_singleton()
        to_create_attachments = []
        report_options = self.env.context["account_report_generation_options"]
        for format in self.export_format_ids:
            # format.fun_to_call is a button function, so it has to be public
            report_action = self.report_id.dispatch_report_action(
                options={**report_options, "report_id": self.report_id.id},
                action=format.fun_to_call,
                action_param=format.fun_param or None,
            )
            to_create_attachments.append(format.apply_export(report_action))

        return to_create_attachments


class Account_ReportsExportWizardFormat(models.TransientModel):
    _name = "account_reports.export.wizard.format"
    _description = "Export format for accounting's reports"

    name = fields.Char(required=True)
    fun_to_call = fields.Char(
        string="Function to Call",
        required=True,
    )
    fun_param = fields.Char(string="Function Parameter")
    export_wizard_id = fields.Many2one(
        comodel_name="account_reports.export.wizard",
        string="Parent Wizard",
        required=True,
        ondelete="cascade",
    )

    @_debug.perf.timed
    def apply_export(self, report_action):
        self.check_singleton()

        _debug.logic(
            "export_action_kind",
            format=self,
            action_type=report_action.get("type"),
        )
        if report_action["type"] == "ir_actions_account_report_download":
            # file_generator functions are always public for ir_actions_account_report_download
            report_options = json.loads(report_action["data"]["options"])
            file_generator = report_action["data"]["file_generator"]
            report = self.export_wizard_id.report_id
            report_options["report_id"] = report.id
            export_result = report.dispatch_report_action(
                report_options, file_generator
            )

            # We use the options from the action, as the action may have added or modified
            # stuff into them (see l10n_es_reports, with BOE wizard)
            file_content = (
                base64.encodebytes(export_result["file_content"])
                if isinstance(export_result["file_content"], bytes)
                else export_result["file_content"]
            )
            # We need to unpack the content in case of a generator
            if isinstance(file_content, types.GeneratorType):
                file_content = base64.encodebytes(b"".join(file_content))
            file_name = f"{self.export_wizard_id.doc_name or self.export_wizard_id.report_id.name}.{export_result['file_type']}"
            mimetype = self.export_wizard_id.report_id.get_export_mime_type(
                export_result["file_type"]
            )
            _debug.pipeline(
                "export_file_generated",
                report=report,
                file_generator=file_generator,
                file_type=export_result.get("file_type"),
                mimetype=mimetype,
            )

        elif report_action["type"] == "ir.actions.act_url":
            query_params = parse_qs(urlparse(report_action["url"]).query)
            model = query_params["model"][0]
            model_id = int(query_params["id"][0])
            wizard = self.env[model].browse(model_id)
            file_name = wizard[query_params["filename_field"][0]]
            file_content = wizard[query_params["field"][0]]
            mimetype = self.env["account.report"].get_export_mime_type(
                file_name.split(".")[-1]
            )

        else:
            raise UserError(
                _("One of the formats chosen can not be exported in the DMS")
            )

        return self._prepare_attachment_vals(
            file_name, file_content, mimetype, report_options
        )

    def _prepare_attachment_vals(
        self, file_name, file_content, mimetype, log_options_dict
    ):
        self.check_singleton()
        return {
            "name": file_name,
            "company_id": self.env.company.id,
            "datas": file_content,
            "mimetype": mimetype,
            "description": json.dumps(log_options_dict),
        }
