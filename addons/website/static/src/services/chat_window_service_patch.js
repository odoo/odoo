/* @odoo-module */

import { ChatWindowService, getVisibleChatWindows } from "@mail/core/common/chat_window_service";
import { patchFn } from "@mail/utils/common/patch";

import { patch } from "@web/core/utils/patch";

let gEnv;

patchFn(getVisibleChatWindows, function () {
    return gEnv.services.website?.context.isPreviewOpen ? [] : this._super();
});

patch(ChatWindowService.prototype, "website/chat_window_service", {
    setup(env, services) {
        this._super(...arguments);
        gEnv = env;
    },
});
