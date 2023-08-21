/* @odoo-module */

import { ChatWindow } from "@mail/core/common/chat_window_model";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow, {
    get visible() {
        return this.env.services.website?.context.isPreviewOpen ? [] : super.visible;
    },
});
