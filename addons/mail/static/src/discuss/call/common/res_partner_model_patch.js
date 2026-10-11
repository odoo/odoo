import { ResPartner } from "@mail/core/common/res_partner_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const resPartnerPatch = patchModel(ResPartner, {
    setup() {
        super.setup(...arguments);
        this.currentRtcSession = fields.One("discuss.channel.rtc.session", {
            inverse: "partner_id",
        });
    },
});
