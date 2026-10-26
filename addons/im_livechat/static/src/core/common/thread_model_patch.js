import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const threadPatch = patchModel(Thread, {
    /**
     * @override
     * @param {import("models").Persona} persona
     */
    getPersonaName(persona) {
        if (this.channel?.channel_type === "livechat" && persona?.user_livechat_username) {
            return persona.user_livechat_username;
        }
        return super.getPersonaName(persona);
    },
});
