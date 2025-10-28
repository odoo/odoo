import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.discuss_category_id = fields.One("discuss.category", {
            inverse: "channel_ids",
        });
    },
    delete() {
        this.store.env.services.bus_service.deleteChannel(this.busChannel);
        super.delete(...arguments);
    },
    /** @override */
    openChannel() {
        if (this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            this.setAsDiscussThread();
            return true;
        }
        return super.openChannel();
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
