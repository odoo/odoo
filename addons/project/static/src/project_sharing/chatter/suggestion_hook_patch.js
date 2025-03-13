import { UseSuggestion } from "@mail/core/common/suggestion_hook";

import { patch } from "@web/core/utils/patch";

patch(UseSuggestion.prototype, {
    async fetchPartners(term, thread, { abortSignal } = {}) {
        if (thread.model === "project.task") {
            const suggestedPartners = await this.ormOnInput(
                "project.task",
                "get_mention_suggestions",
                [thread.id],
                { search: term },
                { abortSignal }
            );
            this.store.insert(suggestedPartners);
            const suggestedPartnersIds = suggestedPartners["res.partner"].map(
                (partner) => partner.id
            );
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
