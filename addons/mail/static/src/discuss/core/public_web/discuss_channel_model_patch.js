import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

const discussChannelPatch = {
    delete() {
        this.store.env.services.bus_service.deleteChannel(this.busChannel);
        super.delete(...arguments);
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
