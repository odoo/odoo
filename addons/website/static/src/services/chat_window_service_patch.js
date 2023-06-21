/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";
import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

let gEnv;

patch(Store.prototype, "website_chat_window_service", {
    get visibleChatWindows() {
        return gEnv.services.website?.context.isPreviewOpen ? [] : this._super();
    },
});

patch(ChatWindowService.prototype, "website/chat_window_service", {
    setup(env, services) {
        this._super(...arguments);
        gEnv = env;
    },
});
