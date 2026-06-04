import { ForwardDialog } from "@mail/discuss/core/common/forward_dialog";

import { patch } from "@web/core/utils/patch";

patch(ForwardDialog.prototype, {
    isDestinationAllowed(channel) {
        return !channel.livechat_end_dt && super.isDestinationAllowed(channel);
    },
});
