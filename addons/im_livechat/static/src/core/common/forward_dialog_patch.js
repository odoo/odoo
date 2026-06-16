import { ForwardDialog } from "@mail/discuss/core/common/forward_dialog";

import { patch } from "@web/core/utils/patch";

/** @type {typeof ForwardDialog} */
const forwardDialogPatch = {
    /**
     * @param {import("models").DiscussChannel} channel
     */
    isDestinationAllowed(channel) {
        return !channel.livechat_end_dt && super.isDestinationAllowed(channel);
    },
};

patch(ForwardDialog.prototype, forwardDialogPatch);
