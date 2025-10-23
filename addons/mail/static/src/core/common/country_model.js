import { ResCountry } from "@mail/core/common/model_definitions";

import { patch } from "@web/core/utils/patch";

patch(ResCountry.prototype, {
    get flagUrl() {
        if (!this.code) {
            return false;
        }
        return `/base/static/img/country_flags/${encodeURIComponent(this.code.toLowerCase())}.png`;
    },
});
