# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.models.mail_message import SHARE_DOMAIN
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler
from odoo.addons.portal.utils import get_portal_partner


class PortalThreadController(ThreadController):
    def _prepare_message_data(self, post_data, *, thread, **kwargs):
        post_data = super()._prepare_message_data(post_data, thread=thread, **kwargs)
        if kwargs.get("from_create") and request.env.user._is_public():
            if partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                post_data["author_id"] = partner.id
        return post_data

    @classmethod
    def _can_edit_message(cls, message, hash=None, pid=None, token=None, **kwargs):
        if message.model and message.res_id and message.env.user._is_public():
            thread = request.env[message.model].browse(message.res_id)
            partner = get_portal_partner(thread, _hash=hash, pid=pid, token=token)
            if partner and message.author_id == partner:
                return True
        return super()._can_edit_message(message, hash=hash, pid=pid, token=token, **kwargs)


class PortalWebClientController(WebclientController):
    @store_handler("/mail/chatter_fetch", audience="everyone")
    def store_mail_chatter_fetch(
        self,
        store: Store,
        thread_model,
        thread_id,
        fetch_params=None,
        **params,
    ):
        # Extract the domain from the `website_message_ids` field to restrict the visible messages according to the model.
        model = request.env[thread_model]
        thread = ThreadController._get_thread_with_access(
            model._name,
            thread_id,
            token=params.get('token'),
        )
        if not thread:
            return
        if portal_partner := get_portal_partner(
            thread,
            _hash=None,
            pid=None,
            token=params.get("token"),
        ):
            request.update_context(
                portal_data={"portal_partner": portal_partner, "portal_thread": thread},
            )
        # All users in the portal see only non-internal messages; internal users are supposed to see
        # the portal as portal users do, so they have the same restriction.
        domain = (
            Domain(self._setup_portal_message_fetch_extra_domain(params))
            & Domain(model._fields['website_message_ids'].get_comodel_domain(model))
            & Domain("res_id", "=", thread.id)
            & ~request.env["mail.message"]._get_empty_domain()
            & request.env["mail.message"]._get_search_domain_share()
            & SHARE_DOMAIN
        )
        # sudo: mail.message - thread access is validated above, and domain is massively restricted to share-only messages
        messages = self._resolve_messages(
            store,
            domain=domain,
            thread=thread,
            fetch_params=fetch_params,
            add_to_store=False,
            sudo=True,
        )
        for message_data in messages.portal_message_format(options=params):
            store.add_model_values("mail.message", message_data)

    @store_handler("/portal/chatter_init", audience="everyone", readonly=False)
    def store_portal_chatter_init(
        self,
        store: Store,
        thread_id,
        thread_model,
        access_params=None,
        **params,
    ):
        access_params = access_params or {}
        store.add_global_values(request.env.user.sudo(False)._store_init_global_fields)
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(request.env.user.partner_id, {"is_user_publisher": True})
        if thread := self._get_thread_with_access(
            thread_model,
            thread_id,
            mode="read",
            **access_params,
        ):
            store.add(
                thread,
                lambda res: self._store_portal_thread_fields(res, access_params),
                as_thread=True,
            )

    @classmethod
    def _store_portal_thread_fields(cls, res: Store.FieldList, access_params):
        portal_partner_by_thread = {
            thread: get_portal_partner(
                # need to use sudo because portal users might not have the right to read the portal partner
                thread.sudo(),
                access_params.get("hash"),
                access_params.get("pid"),
                access_params.get("token"),
            )
            for thread in res.records
        }

        def can_react(thread):
            thread_mode = False
            # sudo: mail.thread - can read thread to build _mail_get_operation_for_mail_message_operation
            for domain, operation in thread.sudo()._mail_get_operation_for_mail_message_operation(
                getattr(thread, "_mail_message_reaction_access", "create"),
            ):
                # sudo: mail.thread - can read thread to filter on access domain
                if thread.sudo().filtered_domain(domain):
                    thread_mode = operation
                    break
            if not thread_mode:
                return False
            has_access = cls._get_thread_with_access(
                thread._name,
                thread.id,
                mode=thread_mode,
                **access_params,
            )
            if request.env.user._is_public():
                return bool(has_access and portal_partner_by_thread.get(thread))
            return bool(has_access)

        res.attr("can_react", can_react)
        res.attr("hasReadAccess", lambda t: t.sudo(False).has_access("read"))
        res.one(
            "portal_partner",
            lambda res: (
                res.attr("active"),
                res.one("main_user_id", ["partner_id", "share"]),
                res.attr("name"),
                res.from_method("_store_avatar_fields"),
            ),
            predicate=lambda t: t in portal_partner_by_thread,
            value=portal_partner_by_thread.get,
        )

    @classmethod
    def _setup_portal_message_fetch_extra_domain(self, data) -> Domain:
        return Domain.TRUE
