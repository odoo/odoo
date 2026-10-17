import { ResPartner } from "@mail/core/common/res_partner_model";
import { patchModel } from "@mail/model/export";

export const resPartnerPatch = patchModel(ResPartner, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} can publish a comment on a rating */
        this.is_user_publisher = undefined;
    },
});
