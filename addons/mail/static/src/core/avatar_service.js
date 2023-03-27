/** @odoo-module */

import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";
import { DEFAULT_AVATAR } from "@mail/core/persona_service";

export class AvatarService {
    /**
     * @param {import('@mail/core/persona_model').Persona} persona
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {integer} personaId
     * @param {string} personaType
     * @param {integer} userId
     * @param {integer} threadId
     * @param {string} threadModel
     */
    getAvatarUrl({ persona, thread, persona_id, persona_type, user_id, thread_id, thread_model }) {
        const threadModel = thread?.model || thread_model;
        const personaType = persona?.type || persona_type;
        const personaId = persona?.id || persona_id;
        const userId = persona?.user?.id || user_id;
        const threadId = thread?.id || thread_id;
        if (threadModel) {
            if (personaType === "partner") {
                return url(`/mail/channel/${threadId}/partner/${personaId}/avatar_128`);
            }
            if (personaType === "guest") {
                return url(`/mail/channel/${threadId}/guest/${personaId}/avatar_128`);
            }
        }
        if (personaType === "partner" && personaId) {
            const avatar = url("/web/image", {
                field: "avatar_128",
                id: personaId,
                model: "res.partner",
            });
            return avatar;
        }
        if (userId) {
            const avatar = url("/web/image", {
                field: "avatar_128",
                id: userId,
                model: "res.users",
            });
            return avatar;
        }
        return DEFAULT_AVATAR;
    }
}

export const avatarService = {
    start(env, services) {
        return new AvatarService(env, services);
    },
};

registry.category("services").add("mail.avatar", avatarService);
