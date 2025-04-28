import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const personaPatch = {
    setup() {
        super.setup();
        this.livechat_languages = [];
        this.livechat_expertise = [];
    },
    _computeDisplayName() {
        return super._computeDisplayName() || this.user_livechat_username;
    },
};
patch(Persona.prototype, personaPatch);
