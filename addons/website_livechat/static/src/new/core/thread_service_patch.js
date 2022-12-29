/** @odoo-module */

import { DEFAULT_AVATAR } from "@mail/new/core/persona_service";
import { ThreadService } from "@mail/new/core/thread_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "website_livechat", {
    update(thread, data) {
        this._super(thread, data);
        if (data.serverData?.visitor) {
            thread.visitor = this.personaService.insert({
                ...data.serverData.visitor,
                type: "visitor",
            });
        }
    },
    /**
     * @param {import('@mail/new/core/persona_model').Persona} persona
     * @param {import("@mail/new/core/thread_model").Thread} [thread]
     */
    avatarUrl(persona, thread) {
        if (persona?.type === "visitor" && thread?.id) {
            return persona.partner
                ? `/mail/channel/${thread.id}/partner/${persona.id}/avatar_128`
                : DEFAULT_AVATAR;
        }
        return this._super(persona, thread);
    },
});
