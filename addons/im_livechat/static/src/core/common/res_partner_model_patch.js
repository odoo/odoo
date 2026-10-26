import { ResPartner } from "@mail/core/common/res_partner_model";
import { patchModel } from "@mail/model/export";

export const resPartnerPatch = patchModel(ResPartner, {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.invite_by_self_count = undefined;
        /** @type {boolean|undefined} */
        this.is_available = undefined;
        /** @type {string|undefined} */
        this.lang_name = undefined;
        /** @type {String[]} */
        this.livechat_languages = [];
        /** @type {string|undefined} */
        this.user_livechat_username = undefined;
    },
    get displayName() {
        return super.displayName || this.user_livechat_username;
    },
});
