import logging
import typing
from collections import defaultdict
from datetime import timedelta
from typing import Literal, Self

from odoo import Command, _, api, fields, models, modules, tools
from odoo.api import ValuesType
from odoo.exceptions import UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import email_normalize, str2bool

from odoo.addons.mail.models.mail_activity import ORPHAN_BUCKET
from odoo.addons.mail.tools.discuss import Store, StoreFieldSpec

if typing.TYPE_CHECKING:
    from collections.abc import Collection

    from .ir_mail_server import IrMail_Server
    from .mail_activity import MailActivity
    from .mail_mail import MailMail
    from .mail_presence import MailPresence
    from .res_role import ResRole

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

ActivityBucket = tuple[str, str]

PERSONAL_MAIL_SERVER_SMTP_PORT = 587
PERSONAL_MAIL_SERVER_SMTP_ENCRYPTION = "starttls"


class ResUsers(models.Model):
    _inherit = "res.users"

    role_ids: ResRole = fields.Many2many(
        comodel_name="res.role",
        relation="res_role_res_users_rel",
        string="User Roles",
        help="Users are notified whenever one of their roles is @-mentioned in a conversation.",
    )
    can_edit_role = fields.Boolean(compute="_compute_can_edit_role")
    notification_type = fields.Selection(
        selection=[("email", "By Emails"), ("inbox", "In Odoo")],
        string="Notification",
        compute="_compute_notification_type",
        inverse="_inverse_notification_type",
        precompute=True,
        store=True,
        required=True,
        help="Policy on how to handle Chatter notifications:\n"
        "- By Emails: notifications are sent to your email address\n"
        "- In Odoo: notifications appear in your Odoo Inbox",
    )
    presence_ids: MailPresence = fields.One2many(
        comodel_name="mail.presence",
        inverse_name="user_id",
        groups="base.group_system",
    )
    out_of_office_from = fields.Datetime()
    out_of_office_to = fields.Datetime()
    out_of_office_message = fields.Html(string="Vacation Responder")
    is_out_of_office = fields.Boolean(
        string="Out of Office",
        compute="_compute_is_out_of_office",
    )
    im_status = fields.Char(
        string="IM Status",
        compute="_compute_im_status",
        compute_sudo=True,
    )
    manual_im_status = fields.Selection(
        selection=[
            ("away", "Away"),
            ("busy", "Do Not Disturb"),
            ("offline", "Offline"),
        ],
        string="IM status manually set by the user",
    )

    outgoing_mail_server_id: IrMail_Server = fields.Many2one(
        comodel_name="ir.mail_server",
        compute="_compute_outgoing_mail_server",
        groups="base.group_user",
    )
    outgoing_mail_server_type = fields.Selection(
        selection=[("default", "Default")],
        compute="_compute_outgoing_mail_server",
        default="default",
        required=True,
        groups="base.group_user",
    )
    has_external_mail_server = fields.Boolean(
        compute="_compute_has_external_mail_server",
        groups="base.group_user",
    )

    _notification_type = models.Constraint(
        "CHECK (notification_type = 'email' OR NOT share)",
        "Only internal user can receive notifications in Odoo",
    )

    @property
    def SELF_READABLE_FIELDS(self) -> list[str]:
        return super().SELF_READABLE_FIELDS + [
            "can_edit_role",
            "is_out_of_office",
            "notification_type",
            "out_of_office_from",
            "out_of_office_message",
            "out_of_office_to",
            "role_ids",
            "has_external_mail_server",
            "outgoing_mail_server_id",
            "outgoing_mail_server_type",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self) -> list[str]:
        return super().SELF_WRITEABLE_FIELDS + [
            "notification_type",
            "out_of_office_from",
            "out_of_office_message",
            "out_of_office_to",
        ]

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        users = super().create(vals_list)
        if any(vals.get("out_of_office_from") for vals in vals_list):
            _debug.lifecycle(
                "out_of_office_cache_cleared", users=users.ids, by="create"
            )
            self.env.registry.clear_cache("stable")
        users._remove_inbox_group_from_shared_users()

        log_portal_access = not self.env.context.get(
            "mail_create_nolog"
        ) and not self.env.context.get("mail_notrack")
        _debug.lifecycle("create", users=users.ids, log_portal_access=log_portal_access)
        if log_portal_access:
            users.filtered(lambda user: user._is_portal())._log_portal_access(True)
        return users

    def write(self, vals: ValuesType) -> Literal[True]:
        log_portal_access = (
            "group_ids" in vals
            and not self.env.context.get("mail_create_nolog")
            and not self.env.context.get("mail_notrack")
        )
        user_portal_access_dict = (
            {user.id: user._is_portal() for user in self} if log_portal_access else {}
        )

        previous_email_by_user = {}
        user_notification_type_modified = self.browse()
        if "email" in vals:
            new_email_normalized = email_normalize(vals["email"] or "")
            previous_email_by_user = {
                user: user.email
                for user in self.filtered(lambda user: bool(user.email_normalized))
                if user.email_normalized != new_email_normalized
            }
        if "notification_type" in vals:
            user_notification_type_modified = self.filtered(
                lambda user: user.notification_type != vals["notification_type"]
            )

        write_res = super().write(vals)
        _debug.lifecycle(
            "write",
            users=self.ids,
            fields=list(vals),
            email_changed=len(previous_email_by_user),
            notification_type_changed=len(user_notification_type_modified),
        )
        if "out_of_office_from" in vals:
            _debug.lifecycle("out_of_office_cache_cleared", users=self.ids, by="write")
            self.env.registry.clear_cache("stable")

        if log_portal_access:
            changed = self.filtered(
                lambda user: user._is_portal() != user_portal_access_dict[user.id]
            )
            for granted, users in changed.grouped(
                lambda user: user._is_portal()
            ).items():
                _debug.logic("portal_access_changed", users=users.ids, granted=granted)
                users._log_portal_access(granted)

        self._notify_security_settings_updated(vals, previous_email_by_user)
        for user in user_notification_type_modified:
            Store(bus_channel=user).add(user, "notification_type").bus_send()
        if "active" in vals and not vals["active"]:
            self._remove_assigned_activities()
        if "group_ids" in vals:
            self._remove_inbox_group_from_shared_users()

        return write_res

    def _log_portal_access(self, granted: bool) -> None:
        self.env["res.partner"]._message_post_values_all(
            {
                user.partner_id.id: {
                    "body": user._get_portal_access_update_body(granted),
                    "message_type": "notification",
                    "subtype_xmlid": "mail.mt_note",
                }
                for user in self
            }
        )

    def unlink(self) -> Literal[True]:
        had_out_of_office = any(user.out_of_office_from for user in self)
        result = super().unlink()
        if had_out_of_office:
            self.env.registry.clear_cache("stable")
        return result

    def _deactivate_portal_user(self, **post) -> None:
        current_user = self.env.user
        for user in self:
            user.partner_id._message_log(
                body=_(
                    "Archived because %(user_name)s (#%(user_id)s) deleted the portal account",
                    user_name=current_user.name,
                    user_id=current_user.id,
                )
            )

        if post.get("request_blacklist"):
            users_to_blacklist = [
                (user, user.email)
                for user in self.filtered(lambda user: email_normalize(user.email))
            ]
        else:
            users_to_blacklist = []
        _debug.lifecycle(
            "portal_user_deactivated",
            users=self.ids,
            by=current_user.id,
            blacklisted=len(users_to_blacklist),
        )

        super(
            ResUsers, self.with_context(mail_notify_security_skip=True)
        )._deactivate_portal_user(**post)

        for user, user_email in users_to_blacklist:
            self.env["mail.blacklist"]._add(
                user_email,
                message=_(
                    "Blocked by deletion of portal account %(portal_user_name)s by %(user_name)s (#%(user_id)s)",
                    user_name=current_user.name,
                    user_id=current_user.id,
                    portal_user_name=user.name,
                ),
            )

    @api.depends_context("uid")
    def _compute_can_edit_role(self) -> None:
        self.can_edit_role = self.env["res.role"].sudo(False).has_access("write")

    def _compute_has_external_mail_server(self) -> None:
        self.has_external_mail_server = str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base_setup.default_external_email_server"),
            False,
        )

    @api.depends("manual_im_status", "presence_ids.status")
    def _compute_im_status(self) -> None:
        for user in self:
            user.im_status = user.presence_ids._fold_im_status(user.manual_im_status)

    @api.depends("out_of_office_from", "out_of_office_to")
    def _compute_is_out_of_office(self) -> None:
        now = self.env.cr.now()
        todo = self.filtered(lambda u: u.out_of_office_from and u._is_internal())
        for user in todo:
            if user.out_of_office_to:
                user.is_out_of_office = (
                    user.out_of_office_from <= now <= user.out_of_office_to
                )
            else:
                user.is_out_of_office = user.out_of_office_from <= now
        (self - todo).is_out_of_office = False

    @api.depends("share", "all_group_ids")
    def _compute_notification_type(self) -> None:
        inbox_group_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.group_mail_notification_type_inbox"
        )

        for user in self:
            user.notification_type = (
                "inbox"
                if inbox_group_id in user.all_group_ids.ids and not user.share
                else "email"
            )

    @api.depends("email")
    def _compute_outgoing_mail_server(self) -> None:
        IrMailServer = self.env["ir.mail_server"].sudo()
        owner_ids = [user._origin.id for user in self if user._origin.id]
        servers_by_owner_id = (
            {
                server.owner_user_id.id: server
                for server in IrMailServer.search([("owner_user_id", "in", owner_ids)])
            }
            if owner_ids
            else {}
        )
        type_options = self._fields["outgoing_mail_server_type"]._selection
        for user in self:
            server = servers_by_owner_id.get(user._origin.id) or IrMailServer.browse()
            if (
                server
                and user.email_normalized
                not in IrMailServer._from_filter_index(server.from_filter).emails
            ):
                server = IrMailServer.browse()
            user.outgoing_mail_server_id = server.id
            user.outgoing_mail_server_type = (
                server.smtp_authentication
                if server.smtp_authentication in type_options
                else "default"
            )

    def _inverse_notification_type(self) -> None:
        inbox_group = self.env.ref("mail.group_mail_notification_type_inbox")
        inbox_users = self.filtered(lambda user: user.notification_type == "inbox")
        inbox_users.write({"group_ids": [Command.link(inbox_group.id)]})
        (self - inbox_users).write({"group_ids": [Command.unlink(inbox_group.id)]})

    @api.model
    def action_setup_outgoing_mail_server(self, server_type: str) -> dict:
        user = self.env.user
        self._check_personal_mail_server_access(user)
        existing_server = (
            self.env["ir.mail_server"]
            .sudo()
            .with_context(active_test=False)
            .search([("owner_user_id", "=", user.id)])
        )

        if server_type == "default":
            existing_server.unlink()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("Switching back to the default server."),
                    "type": "warning",
                },
            }

        self._check_personal_mail_server_type(server_type)
        self._check_personal_mail_server_address(user)

        if server_type == user.outgoing_mail_server_type and (
            server := user.outgoing_mail_server_id
        ):
            return self._get_mail_server_setup_end_action(server)

        existing_server.unlink()
        smtp_server = (
            self.env["ir.mail_server"]
            .sudo()
            .create(self._prepare_personal_mail_server_vals(user, server_type))
        )
        return self._get_mail_server_setup_end_action(smtp_server)

    @api.model
    def action_test_outgoing_mail_server(self) -> dict:
        user = self.env.user
        self._check_personal_mail_server_access(user)
        server_sudo = user.outgoing_mail_server_id.sudo()
        if not server_sudo:
            raise UserError(_("No mail server configured"))
        server_sudo.test_smtp_connection()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("Connection Test Successful!"),
                "type": "success",
            },
        }

    def _notify_security_settings_updated(
        self, vals: ValuesType, previous_email_by_user: dict[Self, str]
    ) -> None:
        if self.env.context.get("mail_notify_security_skip"):
            return
        if _debug.logic.enabled and (
            "login" in vals or "password" in vals or previous_email_by_user
        ):
            _debug.logic(
                "security_notifications",
                users=self.ids,
                login="login" in vals,
                password="password" in vals,
                emails=len(previous_email_by_user),
            )
        if "login" in vals:
            self._notify_security_setting_update(
                _("Security Update: Login Changed"),
                _("Your account login has been updated"),
            )
        if "password" in vals:
            self._notify_security_setting_update(
                _("Security Update: Password Changed"),
                _("Your account password has been updated"),
            )
        for user, previous_email in previous_email_by_user.items():
            user._notify_security_setting_update(
                _("Security Update: Email Changed"),
                _(
                    "Your account email has been changed from %(old_email)s to %(new_email)s.",
                    old_email=previous_email,
                    new_email=user.email or _("no address"),
                ),
                mail_values={"email_to": previous_email},
                suggest_password_reset=False,
            )

    def _notify_security_setting_update(
        self,
        subject: str,
        content: str,
        mail_values: dict | None = None,
        *,
        force_email: str | None = None,
        **kwargs,
    ) -> MailMail:
        mail_create_values = [
            self._prepare_security_alert_mail_vals(
                user, subject, content, force_email=force_email, **kwargs
            )
            | (mail_values or {})
            for user in self
        ]
        mails = self.env["mail.mail"].sudo().create(mail_create_values)
        _debug.lifecycle("security_alert_mails", users=self.ids, mails=mails.ids)
        try:
            mails.send_after_commit()
        except Exception:
            _logger.warning(
                "Could not send security notification email(s) %s",
                mails.ids,
                exc_info=True,
            )
        return mails

    def _prepare_security_alert_mail_vals(
        self,
        user: Self,
        subject: str,
        content: str,
        *,
        force_email: str | None = None,
        **kwargs,
    ) -> dict:
        Render = self.env["mixin.mail.render"]
        body_html = Render._render_template(
            "mail.account_security_alert",
            model="res.users",
            res_ids=user.ids,
            engine="qweb_view",
            options={"post_process": True},
            add_context=user._notify_security_setting_update_prepare_values(
                content, **kwargs
            ),
        )[user.id]
        body_html = Render._render_encapsulate(
            "mail.mail_notification_light",
            body_html,
            add_context={"model_description": _("Account")},
            context_record=user,
        )
        return {
            "auto_delete": True,
            "body_html": body_html,
            "author_id": self.env.user.partner_id.id,
            "email_from": (
                user.company_id.partner_id.email_formatted
                or self.env.user.email_formatted
                or self.env.ref("base.user_root").email_formatted
            ),
            "email_to": force_email or user.email_formatted,
            "subject": subject,
        }

    def _notify_security_setting_update_prepare_values(
        self,
        content: str,
        *,
        suggest_password_reset: bool = True,
        **kwargs,
    ) -> dict:
        reset_password_enabled = str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("auth_signup.reset_password", True)
        )

        values = {
            "browser": False,
            "content": content,
            "event_datetime": fields.Datetime.now(),
            "ip_address": False,
            "location_address": False,
            "suggest_password_reset": suggest_password_reset and reset_password_enabled,
            "user": self,
            "useros": False,
        }
        if not request:
            return values

        geoip = request.geoip
        city = geoip.city.name or False
        region = (geoip.subdivisions[0].name if geoip.subdivisions else False) or False
        country = geoip.country_name or False
        if country:
            if region and city:
                values["location_address"] = _(
                    "Near %(city)s, %(region)s, %(country)s",
                    city=city,
                    region=region,
                    country=country,
                )
            elif region:
                values["location_address"] = _(
                    "Near %(region)s, %(country)s", region=region, country=country
                )
            else:
                values["location_address"] = _("In %(country)s", country=country)
        values["ip_address"] = request.httprequest.remote_addr or False
        if request.httprequest.user_agent:
            if request.httprequest.user_agent.browser:
                values["browser"] = request.httprequest.user_agent.browser.capitalize()
            if request.httprequest.user_agent.platform:
                values["useros"] = request.httprequest.user_agent.platform.capitalize()
        return values

    @api.model
    def _init_store_data(self, store: Store) -> None:
        xmlid_to_res_id = self.env["ir.model.data"]._xmlid_to_res_id
        user = self.env.user
        is_identified = not user._is_public()
        odoobot = self.env.ref("base.partner_root").sudo()
        if is_identified:
            odoobot = odoobot.with_prefetch((odoobot + user.partner_id).ids)
        store.add_global_values(
            action_discuss_id=xmlid_to_res_id("mail.action_discuss"),
            hasLinkPreviewFeature=self.env[
                "mail.link.preview"
            ]._is_link_preview_enabled(),
            internalUserGroupId=self.env.ref("base.group_user").id,
            mt_comment=xmlid_to_res_id("mail.mt_comment"),
            mt_note=xmlid_to_res_id("mail.mt_note"),
            odoobot=Store.One(odoobot),
        )
        if is_identified:
            settings = self.env["res.users.settings"]._get_or_create_for_user(user)
            store.add_global_values(
                self_partner=Store.One(
                    user.partner_id,
                    [
                        "active",
                        "avatar_128",
                        "im_status",
                        Store.One(
                            "main_user_id",
                            [
                                Store.Attr("is_admin", lambda u: u._is_admin()),
                                "notification_type",
                                "partner_id",
                                "share",
                                "signature",
                            ],
                        ),
                        "name",
                    ],
                ),
                settings=settings._res_users_settings_format(),
            )
        if guest := self.env["mail.guest"]._get_guest_from_context():
            store.add_global_values(
                self_guest=Store.One(guest.sudo(), ["avatar_128", "name"])
            )
        _debug.pipeline(
            "store_data_initialized",
            user=user.id,
            identified=is_identified,
            guest=bool(guest),
        )

    def _init_messaging(self, store: Store) -> None:
        self.check_singleton()
        user = self.with_user(self)
        bus_last_id = user.env["bus.bus"].sudo()._bus_last_id()
        store.add_global_values(
            inbox={
                "counter": user.partner_id._get_needaction_count(),
                "counter_bus_id": bus_last_id,
                "id": "inbox",
                "model": "mail.box",
            },
            starred={
                "counter": user.env["mail.message"].search_count(
                    [("starred_partner_ids", "in", user.partner_id.ids)]
                ),
                "counter_bus_id": bus_last_id,
                "id": "starred",
                "model": "mail.box",
            },
        )

    def _get_fields_store_avatar_card(
        self, target: Store.Target
    ) -> list[StoreFieldSpec]:
        return [
            "share",
            Store.One(
                "partner_id", self.partner_id._get_fields_store_avatar_card(target)
            ),
        ]

    @api.model
    def _get_activity_groups(self) -> list:
        activities = self._get_systray_activities()
        activity_ids_by_record = self._group_activity_ids_by_record(activities)
        counts, activity_ids_by_bucket, res_ids_by_bucket = (
            self._count_activities_per_bucket(activity_ids_by_record)
        )
        return self._prepare_activity_group_values(
            counts, activity_ids_by_bucket, res_ids_by_bucket
        )

    @api.model
    def _get_systray_activities(self) -> MailActivity:
        limit = self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.activity.systray.limit", 1000
        )
        activities = (
            self.env["mail.activity"]
            .with_context(active_test=True)
            .search(
                [("user_id", "=", self.env.uid)],
                order="id desc",
                limit=limit,
            )
        )
        _debug.perf.count(
            "systray_activities",
            user=self.env.uid,
            activities=len(activities),
            limit=limit,
        )
        if len(activities) >= limit:
            _logger.warning(
                "Activity systray for user %s read %s activities, its limit "
                "(mail.activity.systray.limit): the counters are undercounts.",
                self.env.uid,
                limit,
            )
        return activities

    @api.model
    def _group_activity_ids_by_record(
        self, activities: MailActivity
    ) -> dict[str, dict[int, list[int]]]:
        activity_ids_by_record = defaultdict(lambda: defaultdict(list))
        for activity in activities:
            if activity.res_model and activity.res_model in self.env:
                activity_ids_by_record[activity.res_model][activity.res_id].append(
                    activity.id
                )
            else:
                activity_ids_by_record[ORPHAN_BUCKET][activity.id].append(activity.id)
        return activity_ids_by_record

    @api.model
    def _activity_bucket_subkeys(
        self, model_name: str, res_ids: Collection[int]
    ) -> dict[int, str]:
        return {}

    @api.model
    def _get_readable_activity_record_ids(
        self, model_name: str, res_ids: Collection[int]
    ) -> tuple[set[int], set[int]]:
        Model = self.env[model_name]
        if not Model.has_access("read"):
            return set(), set(Model.browse(res_ids)._ids)
        existing = Model.browse(res_ids).exists()
        allowed = existing._filtered_access("read")
        unallowed = Model.browse(res_ids) - allowed
        user_company_ids = self.env.user.company_ids.ids
        is_all_user_companies_allowed = set(user_company_ids) == set(
            self.env.context.get("allowed_company_ids") or []
        )
        if unallowed and not is_all_user_companies_allowed:
            unallowed -= (
                (unallowed & existing)
                .with_context(allowed_company_ids=user_company_ids)
                ._filtered_access("read")
            )
        return set(allowed._ids), set(unallowed._ids)

    @api.model
    def _count_activities_per_bucket(
        self, activity_ids_by_record: dict[str, dict[int, list[int]]]
    ) -> tuple[
        dict[ActivityBucket, dict[str, int]],
        dict[ActivityBucket, list[int]],
        dict[ActivityBucket, list[int]],
    ]:
        counts_by_bucket = defaultdict(
            lambda: {
                "overdue_count": 0,
                "today_count": 0,
                "planned_count": 0,
                "due_count": 0,
            }
        )
        activity_ids_by_bucket = defaultdict(list)
        res_ids_by_bucket = defaultdict(list)
        state_by_activity_id = self._get_activity_states(activity_ids_by_record)
        for model_name, activity_ids_by_res_id in activity_ids_by_record.items():
            allowed_ids, unallowed_ids = self._get_readable_activity_record_ids(
                model_name, activity_ids_by_res_id.keys()
            )
            subkeys = self._activity_bucket_subkeys(model_name, allowed_ids)
            for res_id, activity_ids in activity_ids_by_res_id.items():
                if res_id in unallowed_ids:
                    bucket = (ORPHAN_BUCKET, "")
                elif res_id in allowed_ids:
                    bucket = (model_name, subkeys.get(res_id, ""))
                else:
                    continue
                activity_ids_by_bucket[bucket].extend(activity_ids)
                res_ids_by_bucket[bucket].append(res_id)
                states = {
                    state_by_activity_id[activity_id] for activity_id in activity_ids
                }
                if "overdue" in states:
                    counts_by_bucket[bucket]["overdue_count"] += 1
                    counts_by_bucket[bucket]["due_count"] += 1
                elif "today" in states:
                    counts_by_bucket[bucket]["today_count"] += 1
                    counts_by_bucket[bucket]["due_count"] += 1
                else:
                    counts_by_bucket[bucket]["planned_count"] += 1
        return counts_by_bucket, activity_ids_by_bucket, res_ids_by_bucket

    @api.model
    def _get_activity_states(
        self, activity_ids_by_record: dict[str, dict[int, list[int]]]
    ) -> dict[int, str]:
        activities = self.env["mail.activity"].browse(
            [
                activity_id
                for activity_ids_by_res_id in activity_ids_by_record.values()
                for activity_ids in activity_ids_by_res_id.values()
                for activity_id in activity_ids
            ]
        )
        return {activity.id: activity.state for activity in activities}

    @api.model
    def _prepare_activity_group_values(
        self,
        counts_by_bucket: dict[ActivityBucket, dict[str, int]],
        activity_ids_by_bucket: dict[ActivityBucket, list[int]],
        res_ids_by_bucket: dict[ActivityBucket, list[int]],
    ) -> list:
        model_ids = [
            self.env["ir.model"]._get_id(bucket[0]) for bucket in activity_ids_by_bucket
        ]
        model_order = {}
        for bucket in activity_ids_by_bucket:
            model_order.setdefault(bucket[0], len(model_order))
        groups = []
        for bucket in sorted(
            activity_ids_by_bucket, key=lambda b: (model_order[b[0]], b[1])
        ):
            model_name, subkey = bucket
            Model = self.env[model_name]
            module = Model._original_module
            model = self.env["ir.model"]._get(model_name).with_prefetch(model_ids)
            is_orphan_bucket = model_name == ORPHAN_BUCKET
            group = {
                "id": model.id,
                "name": _("Other activities") if is_orphan_bucket else model.name,
                "model": model_name,
                "subkey": subkey,
                "type": "activity",
                "icon": module and modules.module.get_module_icon_path(module),
                "domain": []
                if is_orphan_bucket or "active" not in Model
                else [("active", "in", [True, False])],
                "view_type": getattr(Model, "_systray_view", "list"),
                **counts_by_bucket[bucket],
            }
            if is_orphan_bucket:
                group["activity_ids"] = activity_ids_by_bucket[bucket]
            groups.append(
                self._apply_activity_bucket_subkey(
                    group, model_name, subkey, res_ids_by_bucket[bucket]
                )
            )
        return groups

    @api.model
    def _apply_activity_bucket_subkey(
        self, group: dict, model_name: str, subkey: str, res_ids: list[int]
    ) -> dict:
        return group

    @api.model
    @tools.ormcache(cache="stable")
    def _has_out_of_office_configured(self) -> bool:
        return bool(
            self.sudo()
            .with_context(active_test=False)
            .search_count([("out_of_office_from", "!=", False)], limit=1)
        )

    def _get_portal_access_update_body(self, access_granted: bool) -> str:
        body = (
            _("Portal Access Granted") if access_granted else _("Portal Access Revoked")
        )
        if self.partner_id.email:
            return "%s (%s)" % (body, self.partner_id.email)
        return body

    def _remove_assigned_activities(self) -> None:
        activities = (
            self.env["mail.activity"].sudo().search([("user_id", "in", self.ids)])
        )
        _debug.lifecycle(
            "assigned_activities_removed", users=self.ids, activities=len(activities)
        )
        activities.unlink()

    def _remove_inbox_group_from_shared_users(self) -> None:
        inbox_group_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "mail.group_mail_notification_type_inbox"
        )
        shared_with_inbox = self.filtered_domain(
            [("share", "=", True), ("group_ids", "in", inbox_group_id)]
        )
        if shared_with_inbox:
            _debug.logic("inbox_group_removed_from_shared", users=shared_with_inbox.ids)
            shared_with_inbox.write({"group_ids": [Command.unlink(inbox_group_id)]})

    @api.model
    def _check_personal_mail_server_access(self, user: Self) -> None:
        if not user.has_external_mail_server:
            raise UserError(_("You are not allowed to create a personal mail server."))
        if not user._is_internal():
            raise UserError(
                _("Only internal users can configure a personal mail server.")
            )

    @api.model
    def _check_personal_mail_server_type(self, server_type: str) -> None:
        selection = self._fields["outgoing_mail_server_type"]._description_selection(
            self.env
        )
        if server_type not in dict(selection):
            raise UserError(
                _(
                    "Unknown outgoing mail server type %(server_type)s.",
                    server_type=server_type,
                )
            )

    @api.model
    def _check_personal_mail_server_address(self, user: Self) -> None:
        if not user.email:
            raise UserError(
                _("Please set your email before connecting your mail server.")
            )
        address = user.email_normalized
        if (
            not address
            or address.startswith("@")
            or self.env["ir.mail_server"]._parse_from_filter(address) != [address]
        ):
            raise UserError(_("Wrong email address %s.", user.email))

        alias_domains = self.env["mail.alias.domain"].sudo().search([])
        match_from_filter = self.env["ir.mail_server"]._match_from_filter
        cli_default_from = tools.config.get("email_from")
        if any(
            match_from_filter(default_from, address)
            for default_from in alias_domains.mapped("default_from_email")
        ) or (cli_default_from and match_from_filter(cli_default_from, address)):
            raise UserError(
                _(
                    "Your email address is used by an alias domain, and so you can not create a mail server for it."
                )
            )

    @api.model
    def _prepare_personal_mail_server_vals(self, user: Self, server_type: str) -> dict:
        return {
            "active": False,
            "name": _("%s's outgoing email", user.name),
            "smtp_user": user.email_normalized,
            "smtp_pass": False,
            "from_filter": user.email_normalized,
            "smtp_port": PERSONAL_MAIL_SERVER_SMTP_PORT,
            "smtp_encryption": PERSONAL_MAIL_SERVER_SMTP_ENCRYPTION,
            "owner_user_id": user.id,
            **self._prepare_mail_server_vals(server_type),
        }

    @api.model
    def _prepare_mail_server_vals(self, server_type: str) -> dict:
        return {}

    @api.model
    def _get_mail_server_setup_end_action(self, smtp_server: IrMail_Server) -> dict:
        raise NotImplementedError

    @api.autovacuum
    def _gc_personal_mail_servers(self) -> None:
        IrMailServer = self.env["ir.mail_server"]
        servers = IrMailServer.with_context(active_test=False).search(
            [("owner_user_id", "!=", False)]
        )
        cutoff = self.env.cr.now() - timedelta(
            minutes=IrMailServer._get_personal_mail_server_grace()
        )
        stale = servers.filtered(
            lambda server: (
                server.owner_user_id.outgoing_mail_server_id != server
                if server.active
                else server.create_date < cutoff
            )
        )
        _debug.lifecycle(
            "gc_personal_mail_servers", servers=len(servers), removed=len(stale)
        )
        stale.unlink()
