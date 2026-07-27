# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.discuss.search import SearchController


class LivechatSearchController(SearchController):
    def _store_search_channels_extra(self, store, channels):
        super()._store_search_channels_extra(store, channels)
        if livechats := channels.filtered(lambda c: c.channel_type == "livechat"):
            store.add(livechats._get_last_messages(), "_store_message_fields")
