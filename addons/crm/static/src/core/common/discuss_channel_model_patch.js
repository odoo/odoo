import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.allowCreateLead = this.computed(
            () =>
                this.store.has_access_create_lead &&
                this.store.channel_types_with_lead_command.includes(this.channel_type)
        );
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
