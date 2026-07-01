# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class MessagingMenuController(WebclientController):
    @store_handler("/mail/messaging_menu/initialize_counters", audience="everyone")
    def store_messaging_menu_initialize_counters(
        self,
        store: Store,
        domain_by_tab_id_by_record_type,
    ):
        domain_by_tab_id = domain_by_tab_id_by_record_type.get("mail.message")
        if not domain_by_tab_id:
            return
        messages = self.env["mail.message"].search_fetch(Domain.OR(domain_by_tab_id.values()))
        for tab_id, domain in domain_by_tab_id.items():
            store.add_model_values(
                "MessagingMenuTab",
                {"init_counter_ids": messages.filtered_domain(domain).ids},
                id_data={"id": tab_id},
            )

    @store_handler("/mail/messaging_menu/mail.message/load_more")
    def store_messaging_menu_mail_message_load_more(
        self,
        store: Store,
        domain,
        limit,
        search_term=None,
    ):
        messages = self._resolve_messages(
            store,
            domain=Domain(domain),
            fetch_params={"limit": limit, "search_term": search_term},
        )
        if messages:
            request.update_context(add_inbox_fields=True)
        store.resolve_data_request(
            lambda res: res.attr("is_fully_loaded", len(messages) < limit),
        )
