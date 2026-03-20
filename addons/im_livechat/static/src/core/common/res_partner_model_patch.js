import { ResPartner } from "@mail/core/common/res_partner_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const resPartnerPatch = {
    setup() {
        super.setup();
        /** @type {String[]} */
        this.livechat_languages = [];
    },
    get displayName() {
        return super.displayName || this.user_livechat_username;
    },
};
patch(ResPartner.prototype, resPartnerPatch);
