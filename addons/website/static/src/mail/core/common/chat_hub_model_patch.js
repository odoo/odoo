import { ChatHub } from "@mail/core/common/chat_hub_model";

import { patch } from "@web/core/utils/patch";

export const CHAT_HUB_WE_SIDEBAR_WIDTH = 288; // Same as $o-we-sidebar-width

patch(ChatHub.prototype, {
    computeBubbleStart() {
        if (this.store.env.services["website"]?.context?.edition) {
            return CHAT_HUB_WE_SIDEBAR_WIDTH;
        }
        return super.computeBubbleStart();
    },
});
