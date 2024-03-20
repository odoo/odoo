import { Chatter } from "@mail/chatter/web_portal/chatter";

import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    get afterPostRequestList() {
        return [...super.afterPostRequestList, "followers", "suggestedRecipients"];
    },

    get requestList() {
        return [...super.requestList, "followers", "attachments", "suggestedRecipients"];
    },
});
