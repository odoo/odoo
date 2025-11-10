import { ResPartner } from "@mail/core/common/res_partner_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const resPartnerPatch = {
    setup() {
        super.setup();
        /** @type {String[]} */
        this.livechat_languages = [];
        /**
         * @deprecated Use `user.livechat_expertise_ids` instead.
         * @type {String[]}
         */
        this.livechat_expertise = [];
    },
    _computeDisplayName() {
        return super._computeDisplayName() || this.user_livechat_username;
    },
};
patch(ResPartner.prototype, resPartnerPatch);
