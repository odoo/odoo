/** @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

patch(Persona.prototype, "website_livechat", {
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
        return this._super();
    },
});
