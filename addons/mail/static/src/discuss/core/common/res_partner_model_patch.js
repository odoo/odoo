import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const resPartnerPatch = {
    setup() {
        super.setup();
        this.channelMembers = fields.Many("discuss.channel.member");
    },
};
patch(ResPartner.prototype, resPartnerPatch);
