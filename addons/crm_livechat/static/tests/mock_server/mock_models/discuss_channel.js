import { DiscussChannel } from "@im_livechat/../tests/mock_server/mock_models/discuss_channel";

import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    _types_allowing_lead_command() {
        return super._types_allowing_lead_command(...arguments).concat(["livechat"]);
    },

    _store_livechat_extra_fields(res) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        super._store_livechat_extra_fields(...arguments);
        res.many("livechat_customer_partner_ids", (res) => res.many("opportunity_ids", ["name"]), {
            only_data: true,
            value: (channel) => ResPartner.browse(this._livechat_customer_partner_ids(channel)),
        });
    },
};

patch(DiscussChannel.prototype, discussChannelPatch);
