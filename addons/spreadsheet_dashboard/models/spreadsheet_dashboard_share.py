import base64
import uuid

from werkzeug.exceptions import Forbidden

from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import consteq

_debug = DebugLog(__name__)


class SpreadsheetDashboardShare(models.Model):
    _name = "spreadsheet.dashboard.share"
    _inherit = ["mixin.spreadsheet"]
    _description = "Copy of a shared dashboard"

    dashboard_id = fields.Many2one(
        comodel_name="spreadsheet.dashboard",
        required=True,
        ondelete="cascade",
    )
    excel_export = fields.Binary()
    access_token = fields.Char(
        default=lambda _x: str(uuid.uuid4()),
        required=True,
    )
    full_url = fields.Char(
        string="URL",
        compute="_compute_full_url",
    )
    name = fields.Char(related="dashboard_id.name")

    @api.depends("access_token")
    def _compute_full_url(self):
        for share in self:
            share.full_url = "%s/dashboard/share/%s/%s" % (
                share.get_base_url(),
                share.id,
                share.access_token,
            )

    @api.model
    def action_get_share_url(self, vals):
        if "excel_files" in vals:
            excel_zip = self._zip_xslx_files(vals["excel_files"])
            del vals["excel_files"]
            vals["excel_export"] = base64.b64encode(excel_zip)
        share = self.create(vals)
        _debug.lifecycle(
            "dashboard_share_created",
            share=share,
            dashboard_id=vals.get("dashboard_id"),
            with_excel="excel_export" in vals,
        )
        return share.full_url

    def _is_access_token_matching(self, access_token):
        if not access_token:
            return False
        return consteq(access_token, self.access_token)

    def _check_dashboard_access(self, access_token):
        self.check_singleton()
        token_access = self._is_access_token_matching(access_token)
        dashboard = self.dashboard_id.with_user(self.create_uid)
        user_access = dashboard.has_access("read")
        if not (token_access and user_access):
            _debug.logic(
                "dashboard_share_access_denied",
                share=self,
                token_valid=token_access,
                creator_can_read=user_access,
            )
            raise Forbidden(_("You don't have access to this dashboard. "))
