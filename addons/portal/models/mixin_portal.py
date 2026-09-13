import uuid
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import AccessError


class MixinPortal(models.AbstractModel):
    _name = "mixin.portal"
    _description = "Portal Mixin"

    access_url = fields.Char(
        string="Portal Access URL",
        help="Portal URL for this record (overridden by concrete models).",
        compute="_compute_access_url",
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

    def _portal_ensure_token(self) -> str:
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
            params["access_token"] = self._portal_ensure_token()
        if pid:
            params["pid"] = pid
            params["hash"] = self._sign_token(pid)
        if signup_partner and hasattr(self, "partner_id") and self.partner_id:
            params.update(self.partner_id.signup_get_auth_param()[self.partner_id.id])

        url_base = "/mail/view" if redirect else self.access_url
        qs = urlencode(params)
        return f"{url_base}?{qs}" if qs else url_base

    def _get_access_action(self, access_uid=None, force_website=False):
        self.check_singleton()

        user, record = self.env.user, self
        if access_uid:
            try:
                record.check_access("read")
            except AccessError:
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
                    return {
                        "type": "ir.actions.act_url",
                        "url": record.access_url,
                        "target": "self",
                        "res_id": record.id,
                    }
            else:
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
        params = {"access_token": self._portal_ensure_token()}
        if report_type:
            params["report_type"] = report_type
        if download:
            params["download"] = "true"
        qs = urlencode(params)
        if query_string:
            qs = f"{qs}{query_string}"
        fragment = f"#{anchor}" if anchor else ""
        return f"{self.access_url}{suffix or ''}?{qs}{fragment}"
