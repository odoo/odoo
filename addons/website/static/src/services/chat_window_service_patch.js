/* @odoo-module */

import { ChatWindowService } from "@mail/core/common/chat_window_service";

import { patch } from "@web/core/utils/patch";

patch(ChatWindowService.prototype, {
    get visible() {
        return this.env.services.website?.context.isPreviewOpen ? [] : super.visible;
    },
});
