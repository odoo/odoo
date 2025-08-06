import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";

import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    async restoreDiscussThread() {
        await this.store.channels.fetch();
        return super.restoreDiscussThread(...arguments);
    },
    parseActiveId(rawActiveId) {
        if (typeof rawActiveId === "number") {
            return ["discuss.channel", rawActiveId];
        }
        const parsedActiveId = super.parseActiveId(rawActiveId);
        if (!parsedActiveId) {
            return parsedActiveId;
        }
        const [model, id] = parsedActiveId;
        if (model === "mail.channel") {
            // legacy format (sent in old emails, shared links, ...)
            return ["discuss.channel", id];
        }
        return [model, id];
    },
});
