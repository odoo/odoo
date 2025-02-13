import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    /** @override */
    getSupportedDelimiters(thread) {
        const res = super.getSupportedDelimiters(...arguments);
        return thread.channel_type === "livechat"
            ? res.filter(
                  (delimiter) =>
                      this.store.self.type !== "guest" ||
                      !["#", "/", "::"].includes(delimiter.at(0))
              )
            : res;
    },
});
