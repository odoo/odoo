import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this._prevComposerDisabled = false;
        /** @type {Promise<void>|undefined} */
        this.readyToSwapPromise = undefined;
        /** @type {((value: unknown) => void)|undefined} */
        this.resolveReadyToSwap = undefined;
    },
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
