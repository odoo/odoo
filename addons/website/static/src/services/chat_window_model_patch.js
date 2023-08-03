/* @odoo-module */

import { ChatWindowManager } from "@mail/core/common/chat_window_model";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowManager.prototype, {
    get visible() {
        return this.env.services.website?.context.isPreviewOpen ? [] : super.visible;
    },
});
