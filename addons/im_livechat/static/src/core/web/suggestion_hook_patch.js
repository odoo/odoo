import { UseSuggestion } from "@mail/core/common/suggestion_hook";

import { patch } from "@web/core/utils/patch";

patch(UseSuggestion, {
    getSupportedDelimiters(thread) {
        const res = super.getSupportedDelimiters(...arguments);
        return thread.channel_type === "livechat"
            ? res.filter((delimiter) => delimiter.at(0) !== "#")
            : res;
    },
});
