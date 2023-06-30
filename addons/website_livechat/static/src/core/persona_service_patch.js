/** @odoo-module */

import { PersonaService } from "@mail/core/common/persona_service";
import { patch } from "@web/core/utils/patch";

patch(PersonaService.prototype, "website_livechat", {
    update(persona, data) {
        this._super(persona, data);
        if (persona.type === "visitor") {
            persona.history = data.history ?? persona.history;
            persona.isConnected = data.is_connected ?? persona.isConnected;
            persona.im_status = persona.isConnected ? "online" : undefined;
            persona.langName = data.lang_name ?? persona.langName;
            persona.name = data.display_name ?? persona.name;
            persona.websiteName = data.website_name ?? persona.websiteName;
        }
        if (data.country_id) {
            persona.country = persona.country ?? {};
            persona.country.id = data.country_id;
            persona.country.code = data.country_code ?? persona.country.code;
        }
    },
});
