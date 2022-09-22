/** @odoo-module */

import { Persona } from "@mail/core/persona_model";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, "website_livechat", {
    get countryFlagUrl() {
        const country = this.partner?.country ?? this.country;
        return country
            ? `/base/static/img/country_flags/${encodeURIComponent(country.code.toLowerCase())}.png`
            : undefined;
    },
    get nameOrDisplayName() {
        if (this.partner) {
            return this.partner.nameOrDisplayName;
        }
        return this._super();
    },
});
