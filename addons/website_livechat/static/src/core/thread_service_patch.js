/** @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, "website_livechat", {
    update(thread, data) {
        this._super(thread, data);
        if (data?.visitor) {
            thread.visitor = this.personaService.insert({
                ...data.visitor,
                type: "visitor",
            });
        }
    },
    /**
     * @param {import('@mail/core/common/persona_model').Persona} persona
     * @param {import("@mail/core/common/thread_model").Thread} [thread]
     */
    avatarUrl(persona, thread) {
        if (persona?.type === "visitor" && thread?.id) {
            return persona.partner_id
                ? `/discuss/channel/${encodeURIComponent(thread.id)}/partner/${encodeURIComponent(
                      persona.partner_id
                  )}/avatar_128`
                : DEFAULT_AVATAR;
        }
        return this._super(persona, thread);
    },
});
