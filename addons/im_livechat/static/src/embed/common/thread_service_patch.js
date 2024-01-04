/* @odoo-module */

import { ThreadService } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    /**
     * @returns {Promise<import("models").Message}
     */
    async post(thread, body, params) {
        if (thread.type === "livechat") {
            thread = await this.env.services["im_livechat.livechat"].persist();
            if (!thread) {
                return;
            }
        }
        const message = await super.post(thread, body, params);
        this.env.services["im_livechat.chatbot"].bus.trigger("MESSAGE_POST", message);
        return message;
    },
});
