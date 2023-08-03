/** @odoo-module */

import { Persona, PersonaManager } from "@mail/core/common/persona_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

patch(Persona.prototype, {
    get countryFlagUrl() {
        const country = this.partner?.country ?? this.country;
        return country
            ? `/base/static/img/country_flags/${encodeURIComponent(country.code.toLowerCase())}.png`
            : undefined;
    },
    get nameOrDisplayName() {
        if (this.type === "visitor" && !this.name) {
            return sprintf(_t("Visitor #%s"), this.id);
        }
        return super.nameOrDisplayName;
    },
});

patch(PersonaManager.prototype, {
    update(persona, data) {
        super.update(persona, data);
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
