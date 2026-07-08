import { messagingMenuHelpers } from "@mail/../tests/mock_server/controllers/discuss/messaging_menu";

import { patch } from "@web/core/utils/patch";

// Mirrors `im_livechat/controllers/messaging_menu.py` (LivechatMessagingMenuController):
// registers the livechat tab, on top of mail/discuss's tabs.

patch(messagingMenuHelpers, {
    _get_menu_tab_domain(env, tab_id) {
        if (tab_id === "livechat") {
            return [
                ["channel_type", "=", "livechat"],
                "|",
                ["self_member_id.is_pinned", "=", true],
                ["livechat_status", "=", "need_help"],
            ];
        }
        return super._get_menu_tab_domain(env, tab_id);
    },
    _get_menu_tab_priority_domain(env, tab_id) {
        if (tab_id === "livechat") {
            return [["self_member_id.is_pinned", "=", true]];
        }
        return super._get_menu_tab_priority_domain(env, tab_id);
    },
    _get_menu_tab_filter_domain(env, tab_id, filter_id) {
        if (tab_id === "livechat" && filter_id === "livechat_need_help") {
            return [["livechat_status", "=", "need_help"]];
        }
        return super._get_menu_tab_filter_domain(env, tab_id, filter_id);
    },
});
