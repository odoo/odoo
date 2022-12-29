/** @odoo-module */

import { Persona } from "@mail/new/core/persona_model";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, "website_livechat", {
    get avatarUrl() {
        if (this.type === "visitor") {
            return this.partner?.avatarUrl ?? "/mail/static/src/img/smiley/avatar.jpg";
        }
        return this._super();
    },
    get countryFlagUrl() {
        const country = this.partner?.country ?? this.country;
        return country
            ? `/base/static/img/country_flags/${country.code.toLowerCase()}.png`
            : undefined;
    },
    get nameOrDisplayName() {
        if (this.partner) {
            return this.partner.nameOrDisplayName;
        }
        return this._super();
    },
});
