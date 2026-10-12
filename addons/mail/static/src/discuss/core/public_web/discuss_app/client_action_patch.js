import { DiscussClientAction } from "@mail/core/public_web/discuss_app/client_action";

import { patch } from "@web/core/utils/patch";

patch(DiscussClientAction.prototype, {
    parseActiveId(rawActiveId) {
        if (typeof rawActiveId === "string") {
            const [model, id] = rawActiveId.split("_");
            if (model === "discuss.tab") {
                return ["discuss.tab", id];
            }
            if (model === "mail.box") {
                // Legacy mailbox links (old emails, shared URLs): map to the tabs that
                // replaced the mailboxes. "starred" became "bookmark", "history" and
                // "inbox" became "notification".
                return [
                    "discuss.tab",
                    { starred: "bookmark", history: "notification", inbox: "notification" }[id] ??
                        id,
                ];
            }
        }
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
