/** @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/persona_service";
import { AvatarService } from "@mail/core/avatar_service";
import { patch } from "@web/core/utils/patch";

patch(AvatarService.prototype, "website_livechat", {
    /**
     * @param {import('@mail/core/persona_model').Persona} persona
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {integer} personaId
     * @param {string} personaType
     * @param {integer} userId
     * @param {integer} threadId
     * @param {string} threadModel
     */
    getAvatarUrl({ persona, thread, personaId, personaType, userId, threadId, threadModel}) {
        if (persona?.type === "visitor" && thread?.id) {
            return persona.partner
                ? `/mail/channel/${thread.id}/partner/${persona.id}/avatar_128`
                : DEFAULT_AVATAR;
        }
        return this._super({persona, thread, personaId, personaType, userId, threadId, threadModel});
    },
});
