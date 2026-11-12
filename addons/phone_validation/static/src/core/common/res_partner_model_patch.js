import { ResPartner } from "@mail/core/common/res_partner_model";

import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    setup() {
        super.setup();
        /** @type {string|undefined} */
        this.phone_formatted = undefined;
        /** @type {string|undefined} */
        this.phone_sanitized = undefined;
    },
});
