import { Persona } from "@mail/core/common/persona_model";

import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    get avatarUrl() {
        if (this.store.env.services["portal.chatter"].portalSecurity?.token) {
            return `/web/image/res.partner/${this.id}/avatar_128`;
        }
        return super.avatarUrl;
    },
});
