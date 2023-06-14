/** @odoo-module */

import { DEFAULT_AVATAR, insertPersona } from "@mail/core/common/persona_service";
import { avatarUrl, updateThread } from "@mail/core/common/thread_service";
import { patchFn } from "@mail/utils/common/patch";

/**
 * @param {import('@mail/core/common/persona_model').Persona} persona
 * @param {import("@mail/core/common/thread_model").Thread} [thread]
 */
patchFn(avatarUrl, function (persona, thread) {
    if (persona?.type === "visitor" && thread?.id) {
        return persona.partner
            ? `/discuss/channel/${encodeURIComponent(thread.id)}/partner/${encodeURIComponent(
                  persona.id
              )}/avatar_128`
            : DEFAULT_AVATAR;
    }
    return this._super(persona, thread);
});

patchFn(updateThread, function (thread, data) {
    this._super(thread, data);
    if (data?.visitor) {
        thread.visitor = insertPersona({
            ...data.visitor,
            type: "visitor",
        });
    }
});
