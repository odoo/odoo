import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    get allowCreateLead() {
        return (
            this.store.channel_types_with_create_lead.includes(this.channel_type) &&
            this.store.has_access_create_lead
        );
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
