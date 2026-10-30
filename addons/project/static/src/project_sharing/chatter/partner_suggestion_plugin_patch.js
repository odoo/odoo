import { PartnerSuggestionPlugin } from "@mail/core/common/plugin/suggestion/partner_suggestion_plugin";

import { patch } from "@web/core/utils/patch";

patch(PartnerSuggestionPlugin.prototype, {
    async fetch(cleanedTerm, abortSignal) {
        const thread = this.deps.getThread();
        if (thread?.model === "project.task") {
            this.store.insert(
                await this.callOrm(
                    "project.task",
                    "get_mention_suggestions",
                    [thread.id],
                    { search: cleanedTerm },
                    abortSignal
                )
            );
            return;
        }
        return super.fetch(...arguments);
    },
});
