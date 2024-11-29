import { Persona } from "@mail/core/common/persona_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const personaPatch = {
    setup() {
        super.setup();
        this.channelMembers = Record.many("discuss.channel.member");
    },
};
patch(Persona.prototype, personaPatch);
