import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    get avatarUrl() {
        const token = this.store.env.services["portal.chatter"].token;
        if (token) {
            return `/web/image/res.partner/${this.id}/avatar_128`;
        }
        return super.avatarUrl;
    },
});
