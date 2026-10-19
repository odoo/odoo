import { SUGGESTION_DELIMITERS } from "@mail/core/common/suggestion_hook";
import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    /** @override */
    getSupportedDelimiters(thread) {
        const res = super.getSupportedDelimiters(...arguments);
        return thread?.channel?.channel_type === "livechat" && this.store.self_user?.share !== false
            ? res.filter(([delimiter]) => delimiter !== SUGGESTION_DELIMITERS.PARTNER)
            : res;
    },
});
