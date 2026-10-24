import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields, patchModel } from "@mail/model/export";

export const resPartnerPatch = patchModel(ResPartner, {
    setup() {
        super.setup();
        this.channelMembers = fields.Many("discuss.channel.member");
        /** @type {boolean|undefined} */
        this.is_in_call = undefined;
    },
});
