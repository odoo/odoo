import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const personaPatch = {
    setup() {
        super.setup();
        this.livechat_languages = [];
        this.livechat_expertise = [];
    },
};
patch(Persona.prototype, personaPatch);
