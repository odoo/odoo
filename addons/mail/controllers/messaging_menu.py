# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest

from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class MessagingMenuController(WebclientController):
    def _get_menu_tab_domain(self, tab_id):
        """Resolve a messaging menu tab id to its base ORM domain, restricting which
        records belong to it. `Domain.FALSE` if `tab_id` is unknown to this controller.
        This domain is used both for lazy-loading and to fetch the tab counter.
        """
        partner_id = self.env.user.partner_id.id
        match tab_id:
            case "bookmark":
                return Domain("bookmarked_partner_ids", "=", partner_id)
            case "notification":
                return Domain("notification_ids.res_partner_id", "=", partner_id)
            case _:
                return Domain.FALSE

    def _get_menu_tab_filter_domain(self, tab_id, filter_id):
        """Extra domain ANDed onto `tab_id`'s base domain when `filter_id` is active."""
        if tab_id == "notification" and filter_id == "notification_unread":
            return Domain("needaction", "=", True)
        return Domain.FALSE

    def _get_menu_tab_full_domain(self, tab_id, filter_id):
        """`tab_id`'s domain, ANDed with `filter_id`'s domain if any is given.

        :raise BadRequest: if `tab_id`/`filter_id` don't resolve to a known tab/filter.
        """
        domain = self._get_menu_tab_domain(tab_id)
        if domain is Domain.FALSE:
            raise BadRequest(self.env._("Unknown messaging menu tab %(tab_id)s", tab_id=tab_id))
        if filter_id:
            filter_domain = self._get_menu_tab_filter_domain(tab_id, filter_id)
            if filter_domain is Domain.FALSE:
                err = self.env._(
                    "Unknown messaging menu filter %(filter_id)s for tab %(tab_id)s",
                    filter_id=filter_id,
                    tab_id=tab_id,
                )
                raise BadRequest(err)
            domain &= filter_domain
        return domain

    @store_handler("/mail/messaging_menu/initialize_counters", audience="everyone")
    def store_messaging_menu_initialize_counters(
        self,
        store: Store,
        filter_id_by_tab_id_by_record_type,
    ):
        filter_id_by_tab_id = filter_id_by_tab_id_by_record_type.get("mail.message")
        if not filter_id_by_tab_id:
            return
        domain_by_tab_id = self.get_menu_counter_domain_by_tab_id(filter_id_by_tab_id)
        messages = self.env["mail.message"].search_fetch(Domain.OR(domain_by_tab_id.values()))
        self._add_menu_tab_counters_to_store(store, messages, domain_by_tab_id)

    def get_menu_counter_domain_by_tab_id(self, filter_id_by_tab_id):
        """Resolve the map of tab id to its full domain (taking `tab_id` and `filter_id`
        into account).
        """
        return {
            tab_id: self._get_menu_tab_full_domain(tab_id, filter_id)
            for tab_id, filter_id in filter_id_by_tab_id.items()
        }

    def _add_menu_tab_counters_to_store(self, store, candidate_records, domain_by_tab_id):
        """Store each tab's `init_counter_ids`, taken from `candidate_records` filtered on
        its counter domain."""
        for tab_id, domain in domain_by_tab_id.items():
            store.add_model_values(
                "MessagingMenuTab",
                {"init_counter_ids": candidate_records.filtered_domain(domain).ids},
                id_data={"id": tab_id},
            )

    @store_handler("/mail/messaging_menu/mail.message/load_more")
    def store_messaging_menu_mail_message_load_more(
        self,
        store: Store,
        tab_id,
        limit,
        filter_id=None,
        exclude_ids=None,
        search_term=None,
    ):
        domain = self._get_menu_load_more_domain(tab_id, filter_id, exclude_ids)
        messages = self._resolve_messages(
            store,
            domain=domain,
            fetch_params={"limit": limit, "search_term": search_term},
        )
        if messages:
            request.update_context(add_inbox_fields=True)
        store.resolve_data_request(
            lambda res: res.attr("is_fully_loaded", len(messages) < limit),
        )

    def _get_menu_load_more_domain(self, tab_id, filter_id, exclude_ids):
        """`tab_id`'s (and `filter_id`'s) domain, excluding `exclude_ids`."""
        domain = self._get_menu_tab_full_domain(tab_id, filter_id)
        if exclude_ids:
            domain &= Domain("id", "not in", exclude_ids)
        return domain
