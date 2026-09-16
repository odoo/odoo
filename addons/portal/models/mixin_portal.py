import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog

from odoo.addons.portal.utils import get_url_with_params

_debug = DebugLog(__name__)


class MixinPortal(models.AbstractModel):
    _name = "mixin.portal"
    _description = "Portal Mixin"

    access_url = fields.Char(
        string="Portal Access URL",
        compute="_compute_access_url",
        help="Portal URL for this record (overridden by concrete models).",
    )
    access_token = fields.Char(
        string="Security Token",
        copy=False,
    )

    access_warning = fields.Text(
        string="Access warning",
        compute="_compute_access_warning",
    )

    def _compute_access_warning(self):
        for record in self:
            record.access_warning = ""

    def _compute_access_url(self):
        for record in self:
            record.access_url = "#"

    def _portal_get_or_create_token(self) -> str:
        self.check_singleton()
        if not self.access_token:
            self.sudo().write({"access_token": str(uuid.uuid4())})
        return self.access_token

    def _get_share_url(
        self, redirect=False, signup_partner=False, pid=None, share_token=True
    ):
        self.check_singleton()
        params = {"model": self._name, "res_id": self.id} if redirect else {}
        if share_token:
            self.check_access("read")
            params["access_token"] = self._portal_get_or_create_token()
        if pid:
            params["pid"] = pid
            params["hash"] = self._sign_token(pid)
        if signup_partner and hasattr(self, "partner_id") and self.partner_id:
            params.update(self.partner_id.signup_get_auth_param()[self.partner_id.id])

        url_base = "/mail/view" if redirect else self.access_url
        return get_url_with_params(url_base, params)

    def _get_access_action(self, access_uid=None, force_website=False):
        self.check_singleton()

        user, record = self.env.user, self
        if access_uid:
            try:
                record.check_access("read")
            except AccessError:
                _debug.logic(
                    "access_action",
                    by="super_no_read",
                    model=self._name,
                    record=self.id,
                )
                return super()._get_access_action(
                    access_uid=access_uid, force_website=force_website
                )
            user = self.env["res.users"].sudo().browse(access_uid)
            record = self.with_user(user)
        if user.share or force_website:
            try:
                record.check_access("read")
            except AccessError:
                if force_website:
                    _debug.logic(
                        "access_action",
                        by="access_url",
                        model=self._name,
                        record=self.id,
                    )
                    return {
                        "type": "ir.actions.act_url",
                        "url": record.access_url,
                        "target": "self",
                        "res_id": record.id,
                    }
            else:
                _debug.logic(
                    "access_action", by="share_url", model=self._name, record=self.id
                )
                return {
                    "type": "ir.actions.act_url",
                    "url": record._get_share_url(),
                    "target": "self",
                    "res_id": record.id,
                }
        return super()._get_access_action(
            access_uid=access_uid, force_website=force_website
        )

    @api.model
    def action_share(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "portal.portal_share_action"
        )
        action["context"] = {
            "active_id": self.env.context.get("active_id"),
            "active_model": self.env.context.get("active_model"),
            **self.env["ir.actions.actions"]._eval_action_context(action["context"]),
        }
        return action

    def get_portal_url(
        self,
        suffix=None,
        report_type=None,
        download=None,
        query_string=None,
        anchor=None,
    ) -> str:
        self.check_singleton()
        params = {"access_token": self._portal_get_or_create_token()}
        if report_type:
            params["report_type"] = report_type
        if download:
            params["download"] = "true"
        url = urlsplit(self.access_url)
        query = parse_qsl(url.query, keep_blank_values=True)
        if query_string:
            query.extend(parse_qsl(query_string.lstrip("?&"), keep_blank_values=True))
        url = urlunsplit(
            url._replace(
                path=url.path + (suffix or ""),
                query=urlencode(query),
                fragment=anchor if anchor is not None else url.fragment,
            )
        )
        # Credentials and explicit options take priority over query-string values.
        return get_url_with_params(url, params)
