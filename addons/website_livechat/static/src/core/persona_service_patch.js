/** @odoo-module */

import { insertPersona, updatePersona } from "@mail/core/common/persona_service";
import { patchFn } from "@mail/utils/common/patch";

patchFn(updatePersona, function (persona, data) {
    this._super(persona, data);
    if (persona.type === "visitor") {
        persona.history = data.history ?? persona.history;
        persona.isConnected = data.is_connected ?? persona.isConnected;
        persona.im_status = persona.isConnected ? "online" : undefined;
        persona.langName = data.lang_name ?? persona.langName;
        persona.name = data.display_name ?? persona.name;
        persona.websiteName = data.website_name ?? persona.websiteName;
        if (data.country_id) {
            persona.country = persona.country ?? {};
            persona.country.id = data.country_id;
            persona.country.code = data.country_code ?? persona.country.code;
        }
        if (data.partner_id) {
            persona.partner = insertPersona({
                id: data.partner_id,
                type: "partner",
            });
        }
    }
});
