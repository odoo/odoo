import { Message } from "@mail/core/common/message";
import { SubChannelPreview } from "@mail/discuss/core/public_web/sub_channel_preview";

import { patch } from "@web/core/utils/patch";

Object.assign(Message.components, { SubChannelPreview });

patch(Message.prototype, {
    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickNotificationMessage(ev) {
        const { oeType } = ev.target.dataset;
        if (oeType === "sub-channels-menu") {
            this.env.subChannelMenu?.open();
        }
        await super.onClickNotificationMessage(...arguments);
    },
});
