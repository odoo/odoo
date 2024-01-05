/* @odoo-module */

import { DiscussClientAction } from "@mail/core/web/discuss_client_action";

import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    async restoreDiscussThread() {
        await this.store.fetchChannels();
        return super.restoreDiscussThread(...arguments);
    },
    parseActiveId(rawActiveId) {
        if (typeof rawActiveId === "number") {
            return ["discuss.channel", rawActiveId];
        }
        const [model, id] = super.parseActiveId(rawActiveId);
        if (model === "mail.channel") {
            // legacy format (sent in old emails, shared links, ...)
            return ["discuss.channel", id];
        }
        return [model, id];
    },
});
