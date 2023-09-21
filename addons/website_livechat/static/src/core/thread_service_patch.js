/** @odoo-module */

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { ThreadService } from "@mail/core/common/thread_service";
import { assignDefined } from "@mail/utils/common/misc";
import { patch } from "@web/core/utils/patch";

patch(ThreadService.prototype, {
    update(thread, data) {
        super.update(thread, data);
        if (data?.visitor) {
            thread.visitor = this.store.Persona.insert({
                ...data.visitor,
                type: "visitor",
            });
        }
        assignDefined(thread, data, ["requested_by_operator"]);
    },
    /**
     * @param {import("models").Persona} persona
     * @param {import("models").Thread} [thread]
     */
    avatarUrl(persona, thread) {
        if (persona?.type === "visitor" && thread?.id) {
            return persona.partner_id
                ? `/discuss/channel/${encodeURIComponent(thread.id)}/partner/${encodeURIComponent(
                      persona.partner_id
                  )}/avatar_128`
                : DEFAULT_AVATAR;
        }
        return super.avatarUrl(persona, thread);
    },
});
