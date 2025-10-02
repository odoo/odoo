import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    /** @override */
    getSupportedDelimiters(thread, env) {
        const res = super.getSupportedDelimiters(...arguments);
        return thread.channel?.channel_type === "livechat"
            ? res.filter((delimiter) => delimiter.at(0) !== "#")
            : res;
    },
});
