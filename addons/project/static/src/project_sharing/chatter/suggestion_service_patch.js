import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    async fetchPartners(term, thread, { abortSignal } = {}) {
        if (thread.model === "project.task") {
            const suggestedPartners = await this.makeOrmCall(
                "project.task",
                "get_mention_suggestions",
                [thread.id],
                { search: term },
                { abortSignal }
            );
            this.store.insert(suggestedPartners);
            thread.limitedMentions = suggestedPartners["res.partner"];
        }
        return super.fetchPartners(...arguments);
    },

    getPartnerSuggestions(thread) {
        if (thread.model === "project.task") {
            return thread.limitedMentions;
        }
        return super.getPartnerSuggestions(...arguments);
    },
});
