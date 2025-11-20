import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

patch(DiscussChannel.prototype, {
    setup() {
        super.setup(...arguments);
        this.shadowedBySelf = 0;
    },
    get shouldSubscribeToBusChannel() {
        return super.shouldSubscribeToBusChannel || Boolean(this.shadowedBySelf);
    },
});
