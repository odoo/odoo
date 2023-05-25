/* @odoo-module */

import { ChatWindowService } from "@mail/web/chat_window/chat_window_service";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, "website/chat_window_service", {
    get visible() {
        return this.env.services.website?.context.isPreviewOpen ? [] : this._super();
    },
});
