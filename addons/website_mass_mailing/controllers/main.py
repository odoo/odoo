from odoo import Command, _, tools
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.libs.debug_log import DebugLog

from odoo.addons.mass_mailing.controllers import main

_debug = DebugLog(__name__)


class MassMailController(main.MassMailController):
    @route(
        "/website_mass_mailing/is_subscriber",
        type="jsonrpc",
        website=True,
        auth="public",
    )
    def is_subscriber(self, list_id, subscription_type, **post):
        value = self._get_value(subscription_type)
        fname = self._get_fname(subscription_type)
        is_subscriber = False
        if value and fname:
            search_fname, _create_value = self._contact_value_lookup(fname, value)
            contacts_count = (
                request.env["mailing.subscription"]
                .sudo()
                .search_count(
                    [
                        ("list_id", "in", [int(list_id)]),
                        (f"contact_id.{search_fname}", "=", value),
                        ("opt_out", "=", False),
                    ]
                )
            )
            is_subscriber = contacts_count > 0

        _debug.logic(
            "is_subscriber",
            list_id=list_id,
            subscription_type=subscription_type,
            has_value=bool(value),
            is_subscriber=is_subscriber,
        )
        return {"is_subscriber": is_subscriber, "value": value}

    def _get_value(self, subscription_type):
        value = None
        if subscription_type == "email":
            if not request.env.user._is_public():
                value = request.env.user.email
            elif request.session.get("mass_mailing_email"):
                value = request.session["mass_mailing_email"]
        return value

    def _get_fname(self, subscription_type):
        return "email" if subscription_type == "email" else ""

    @staticmethod
    def _contact_value_lookup(fname, value):
        field = request.env["mailing.contact"]._fields[fname]
        if field.type == "many2many" and field.comodel_name == "phone.number":
            return "phone_mobile_search", [
                Command.create({"number": value, "type": "mobile"})
            ]
        return fname, value

    @route(
        "/website_mass_mailing/subscribe", type="jsonrpc", website=True, auth="public"
    )
    def subscribe(self, list_id, value, subscription_type, **post):
        try:
            request.env["ir.http"]._check_request_recaptcha_token(
                "website_mass_mailing_subscribe"
            )
        except UserError as e:
            _debug.logic("subscribe_recaptcha_refused", list_id=list_id, error=e)
            return {
                "toast_type": "danger",
                "toast_content": str(e),
            }

        fname = self._get_fname(subscription_type)
        self.subscribe_to_newsletter(subscription_type, value, list_id, fname)
        return {
            "toast_type": "success",
            "toast_content": _("Thanks for subscribing!"),
        }

    @staticmethod
    def subscribe_to_newsletter(
        subscription_type, value, list_id, fname, address_name=None
    ):
        ContactSubscription = request.env["mailing.subscription"].sudo()
        Contacts = request.env["mailing.contact"].sudo()
        if subscription_type == "email":
            name, value = tools.parse_contact_from_email(value)
            if not name:
                name = address_name
        elif subscription_type == "mobile":
            name = value

        search_fname, create_value = MassMailController._contact_value_lookup(
            fname, value
        )
        subscription = ContactSubscription.search(
            [
                ("list_id", "=", int(list_id)),
                (f"contact_id.{search_fname}", "=", value),
            ],
            limit=1,
        )
        if not subscription:
            contact_id = Contacts.search([(search_fname, "=", value)], limit=1)
            if not contact_id:
                contact_id = Contacts.create({"name": name, fname: create_value})
                _debug.lifecycle(
                    "mailing_contact_created",
                    contact=contact_id,
                    list_id=list_id,
                    subscription_type=subscription_type,
                )
            ContactSubscription.create(
                {"contact_id": contact_id.id, "list_id": int(list_id)}
            )
            _debug.lifecycle(
                "subscription_created", contact=contact_id, list_id=list_id
            )
        elif subscription.opt_out:
            _debug.lifecycle("subscription_opt_in_restored", subscription=subscription)
            subscription.opt_out = False
        request.session[f"mass_mailing_{fname}"] = value
