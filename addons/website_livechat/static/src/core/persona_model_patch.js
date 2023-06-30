/** @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, "website_livechat", {
    get countryFlagUrl() {
        return this.country
            ? `/base/static/img/country_flags/${encodeURIComponent(
                  this.country.code.toLowerCase()
              )}.png`
            : undefined;
    },
});
