import { SuggestionService } from "@mail/core/common/suggestion_service";

import { patch } from "@web/core/utils/patch";

patch(SuggestionService.prototype, {
    async fetchPartners(term, thread) {
        const kwargs = { search: term };
        if (thread.model === "project.task") {
            kwargs.task_id = thread.id;
            const suggestedPartners = await this.orm.silent.call(
                "res.partner",
                "get_mention_suggestions_from_task",
                [],
                kwargs
            );
            this.store.Persona.insert(suggestedPartners);
            const suggestedPartnersIds = suggestedPartners.map((partner) => partner.id);
            thread.limitedMentions = Object.values(this.store.Persona.records).filter((persona) =>
                suggestedPartnersIds.includes(persona.id)
            );
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
