/** @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    update(data) {
        super.update(data);
        if (this.type === "visitor") {
            this.history = data.history ?? this.history;
            this.isConnected = data.is_connected ?? this.isConnected;
            this.im_status = this.isConnected ? "online" : undefined;
            this.langName = data.lang_name ?? this.langName;
            this.name = data.display_name ?? this.name;
            this.websiteName = data.website_name ?? this.websiteName;
        }
        if (data.country_id) {
            this.country = this.country ?? {};
            this.country.id = data.country_id;
            this.country.code = data.country_code ?? this.country.code;
        }
    },
    get countryFlagUrl() {
        const country = this.partner?.country ?? this.country;
        return country
            ? `/base/static/img/country_flags/${encodeURIComponent(country.code.toLowerCase())}.png`
            : undefined;
    },
    get nameOrDisplayName() {
        if (this.type === "visitor" && !this.name) {
            return _t("Visitor #%s", this.id);
        }
        return super.nameOrDisplayName;
    },
});
