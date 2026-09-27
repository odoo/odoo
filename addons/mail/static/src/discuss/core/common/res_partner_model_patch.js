import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Persona} */
const resPartnerPatch = {
    setup() {
        super.setup();
        this.channelMembers = fields.Many("discuss.channel.member");
        /** @type {boolean|undefined} */
        this.is_in_call = undefined;
    },
};
patch(ResPartner.prototype, resPartnerPatch);
