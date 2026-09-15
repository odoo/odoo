import logging
from collections import defaultdict

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class WebsiteMail(http.Controller):
    @http.route(["/website_mail/follow"], type="jsonrpc", auth="public", website=True)
    def website_message_subscribe(
        self, id=0, object=None, message_is_follower="on", email=False, **post
    ):
        res_id = int(id)
        is_follower = message_is_follower == "on"
        record = request.env[object].browse(res_id).exists()
        if not record:
            return False

        record.check_access("read")

        if request.env.user != request.website.user_id:
            partner_ids = request.env.user.partner_id.ids
        else:
            try:
                self.env["ir.http"]._check_request_recaptcha_token(
                    "website_mail_follow"
                )
            except (ValidationError, UserError) as e:
                _logger.debug(
                    "website_mail_follow recaptcha check failed, "
                    "falling back to no_create: %s",
                    e,
                )
                no_create = True
            else:
                no_create = False
            partner_ids = (
                record.sudo()
                ._partner_get_or_create_from_emails_single([email], no_create=no_create)
                .ids
            )
            if not partner_ids:
                _debug.logic(
                    "follow_partner_unresolved",
                    model=object,
                    res_id=res_id,
                    no_create=no_create,
                )
                return False
        if is_follower:
            _debug.lifecycle(
                "unsubscribed", model=object, res_id=res_id, partners=partner_ids
            )
            record.sudo().message_unsubscribe(partner_ids)
            return False
        else:
            _debug.lifecycle(
                "subscribed", model=object, res_id=res_id, partners=partner_ids
            )
            request.session["partner_id"] = partner_ids[0]
            record.sudo().message_subscribe(partner_ids)
            return True

    @http.route(
        ["/website_mail/is_follower"],
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def is_follower(self, records, **post):
        user = request.env.user
        partner = None
        public_user = request.website.user_id
        if user != public_user:
            partner = request.env.user.partner_id
        elif request.session.get("partner_id"):
            partner = (
                request.env["res.partner"]
                .sudo()
                .browse(request.session.get("partner_id"))
            )

        _debug.logic(
            "is_follower_identity",
            is_user=user != public_user,
            partner=partner,
            models=len(records),
        )
        res = defaultdict(list)
        if partner:
            for model in records:
                mail_followers_ids = (
                    request.env["mail.followers"]  # noqa: E8507 - one query per model of the request
                    .sudo()
                    ._read_group(
                        [
                            ("res_model", "=", model),
                            ("res_id", "in", records[model]),
                            ("partner_id", "=", partner.id),
                        ],
                        ["res_id"],
                    )
                )
                res[model].extend(res_id for [res_id] in mail_followers_ids)

        return [
            {
                "is_user": user != public_user,
                "email": partner.email if partner else "",
            },
            res,
        ]
