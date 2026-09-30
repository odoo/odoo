import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    async fetchPartnersRoles(term, thread, { abortSignal } = {}) {
        if (thread.model === "project.task") {
            this.store.insert(
                await this.makeOrmCall(
                    "project.task",
                    "get_mention_suggestions",
                    [thread.id],
                    { search: term },
                    { abortSignal }
                )
            );
            return;
        }
        return super.fetchPartnersRoles(...arguments);
    },
});
