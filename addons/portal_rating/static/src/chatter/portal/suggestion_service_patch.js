import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    getSupportedDelimiters(thread, env) {
        if (thread?.reviewChatter) {
            return [];
        }
        return super.getSupportedDelimiters(thread, env);
    },
});
