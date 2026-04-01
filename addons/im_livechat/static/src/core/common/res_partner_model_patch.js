import { ResPartner } from "@mail/core/common/res_partner_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const resPartnerPatch = {
    get displayName() {
        return (
            super.displayName || this.user_livechat_username || this.main_user_id?.livechat_username
        );
    },
};
patch(ResPartner.prototype, resPartnerPatch);
