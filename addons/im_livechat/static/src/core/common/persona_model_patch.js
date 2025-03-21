import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const personaPatch = {
    setup() {
        super.setup();
        this.livechat_languages = [];
        this.livechat_expertise = [];
    },
    getContextualName(channel) {
        if (channel.channel_type === "livechat" && this.user_livechat_username) {
            return this.user_livechat_username;
        }
        return super.getContextualName(channel);
    },
};
patch(Persona.prototype, personaPatch);
