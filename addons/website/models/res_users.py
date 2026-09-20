import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    website_id = fields.Many2one(  # noqa: E8529  UNIQUE (login, website_id)
        comodel_name="website",
        related="partner_id.website_id",
        related_sudo=False,
        store=True,
        readonly=False,
    )

    _login_key = models.UniqueIndex(
        "(login, website_id) WHERE website_id IS NOT NULL",
        "You can not have two users with the same login!",
    )

    @api.constrains("login", "website_id")
    def _check_login(self):
        self.flush_model(["login", "website_id"])
        self.env.cr.execute(
            """SELECT login
                 FROM res_users
                WHERE login IN (SELECT login FROM res_users WHERE id = ANY(%s) AND website_id IS NULL)
                  AND website_id IS NULL
             GROUP BY login
               HAVING COUNT(*) > 1
            """,
            (list(self.ids),),
        )
        if self.env.cr.rowcount:
            _debug.logic(
                "user_login_refused", reason="duplicate", users=self, count=len(self)
            )
            raise ValidationError(_("You can not have two users with the same login!"))

    @api.model
    def _get_domain_login(self, login):
        website = self.env["website"].get_current_website()
        return super()._get_domain_login(login) & website.website_domain()

    @api.model
    def _get_domain_email(self, email):
        website = self.env["website"].get_current_website()
        return super()._get_domain_email(email) & website.website_domain()

    @api.model
    def _get_login_order(self):
        return "website_id, " + super()._get_login_order()

    @api.model
    def _signup_create_user(self, values):
        current_website = self.env["website"].get_current_website()
        values["company_id"] = current_website.company_id.id
        values["company_ids"] = [Command.link(current_website.company_id.id)]
        if request and current_website.specific_user_account:
            values["website_id"] = current_website.id
        _debug.lifecycle(
            "signup_user",
            website=current_website.id,
            company=current_website.company_id.id,
            specific=bool(values.get("website_id")),
        )
        return super()._signup_create_user(values)

    @api.model
    def _get_signup_invitation_scope(self):
        current_website = self.env["website"].sudo().get_current_website()
        return (
            current_website.auth_signup_uninvited
            or super()._get_signup_invitation_scope()
        )

    def authenticate(self, credential, user_agent_env):
        visitor_pre_authenticate_sudo = None
        if request and request.env:
            visitor_pre_authenticate_sudo = request.env[
                "website.visitor"
            ]._get_visitor_from_request()
        auth_info = super().authenticate(credential, user_agent_env)
        if auth_info.get("uid") and visitor_pre_authenticate_sudo:
            env = self.env(user=auth_info["uid"])
            user_partner = env.user.partner_id
            visitor_current_user_sudo = (
                env["website.visitor"]
                .sudo()
                .search([("partner_id", "=", user_partner.id)], limit=1)
            )
            if visitor_current_user_sudo:
                if visitor_pre_authenticate_sudo != visitor_current_user_sudo:
                    _debug.lifecycle(
                        "visitor_merged_on_login",
                        user=auth_info["uid"],
                        anonymous=visitor_pre_authenticate_sudo.id,
                        known=visitor_current_user_sudo.id,
                    )
                    visitor_pre_authenticate_sudo._merge_visitor(
                        visitor_current_user_sudo
                    )
                visitor_current_user_sudo._update_visitor_last_visit()
            else:
                _debug.lifecycle(
                    "visitor_claimed_on_login",
                    user=auth_info["uid"],
                    visitor=visitor_pre_authenticate_sudo.id,
                    partner=user_partner.id,
                )
                visitor_pre_authenticate_sudo.access_token = user_partner.id
                visitor_pre_authenticate_sudo._update_visitor_last_visit()
        return auth_info

    @api.constrains("group_ids")
    def _check_disjoint_groups(self):
        super()._check_disjoint_groups()
        internal_users = self.env.ref("base.group_user").all_user_ids & self
        if any(user.website_id for user in internal_users):
            _debug.logic(
                "internal_user_refused",
                reason="partner_bound_to_website",
                users=internal_users,
            )
            raise ValidationError(
                _("Remove website on related partner before they become internal user.")
            )

    def website_publish_button(self):
        return self.partner_id.website_publish_button()
