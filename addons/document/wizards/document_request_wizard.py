from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_timedelta, time_unit_selection
from odoo.tools.misc import clean_context

_debug = DebugLog(__name__)


class DocumentsRequest_Wizard(models.TransientModel):
    _name = "document.request_wizard"
    _description = "Document Request"

    name = fields.Char(required=True)
    requestee_id = fields.Many2one(
        comodel_name="res.partner",
        string="Owner",
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
    )

    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activity type",
        default=lambda self: self.env.ref(
            "mail.mail_activity_data_upload_document", raise_if_not_found=False
        ),
        required=True,
        domain="[('category', '=', 'upload_file')]",
    )

    tag_ids = fields.Many2many(
        comodel_name="document.tag",
        string="Tags",
    )
    folder_id = fields.Many2one(
        comodel_name="document.document",
        domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]",
    )

    res_model = fields.Char(string="Resource Model")
    res_id = fields.Integer(string="Resource ID")

    activity_note = fields.Html(string="Message")
    activity_date_deadline_range = fields.Integer(
        string="Due Date In",
        default=30,
    )
    activity_date_deadline_range_type = fields.Selection(
        selection=time_unit_selection("day", "week", "month"),
        string="Due type",
        default="day",
    )

    @api.onchange("activity_type_id")
    def _on_activity_type_change(self) -> None:
        if self.activity_type_id:
            if not self.tag_ids:
                self.tag_ids = self.activity_type_id.tag_ids
            if not self.folder_id:
                self.folder_id = self.activity_type_id.folder_id
            if not self.requestee_id:
                self.requestee_id = self.activity_type_id.default_user_id.partner_id

    def request_document(self) -> models.Model:
        self.check_singleton()
        if self.res_model and self.res_id:
            if self.res_model not in self.env:
                _debug.logic(
                    "request_refused", reason="unknown_model", model=self.res_model
                )
                raise UserError(_("Invalid model %s.", self.res_model))
            self.env[self.res_model].browse(self.res_id).check_access("write")
        document = self.env["document.document"].create(
            {
                "name": self.name,
                "folder_id": self.folder_id.id,
                "tag_ids": [(6, 0, self.tag_ids.ids if self.tag_ids else [])],
                "partner_id": self.partner_id.id if self.partner_id else False,
                "requestee_partner_id": self.requestee_id.id,
                "res_model": self.res_model,
                "res_id": self.res_id,
            }
        )

        activity_vals = {
            "user_id": self.requestee_id.main_user_id.id
            if self.requestee_id.main_user_id
            else self.env.user.id,
            "note": self.activity_note,
            "activity_type_id": self.activity_type_id.id
            if self.activity_type_id
            else False,
            "summary": self.name,
        }

        if self.activity_date_deadline_range > 0:
            activity_vals["date_deadline"] = fields.Date.context_today(
                self
            ) + get_timedelta(
                self.activity_date_deadline_range,
                self.activity_date_deadline_range_type,
            )

        request_by_mail = (
            self.requestee_id and self.create_uid not in self.requestee_id.user_ids
        )
        _debug.lifecycle(
            "document_requested",
            document=document,
            requestee=self.requestee_id,
            by_mail=bool(request_by_mail),
        )
        activity = document.with_context(
            mail_activity_quick_update=request_by_mail
        ).activity_schedule(**activity_vals)
        document.request_activity_id = activity

        if self.requestee_id.user_ids:
            partners = {
                self.requestee_id.id: (
                    "edit",
                    datetime.combine(activity.date_deadline, datetime.max.time()),
                ),
            }
            partners[self.env.user.partner_id.id] = ("edit", False)
            document.action_update_access_rights("none", partners=partners)
        else:
            document.access_via_link = "edit"
            document.action_update_access_rights(
                "none", partners={self.env.user.partner_id.id: ("edit", False)}
            )
        request_template = self.env.ref(
            "document.mail_template_document_request", raise_if_not_found=False
        )
        if request_template:
            document.with_context(
                clean_context(self.env.context)
            ).message_mail_with_source(request_template)

        return document
