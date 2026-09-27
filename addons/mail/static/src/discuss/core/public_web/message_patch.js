import { Message } from "@mail/core/common/message";
import { SubChannelPreview } from "@mail/discuss/core/public_web/sub_channel_preview";

import { patch } from "@web/core/utils/patch";

Object.assign(Message.components, { SubChannelPreview });

patch(Message.prototype, {
    /**
     * @type {ReturnType<typeof import("@mail/discuss/core/public_web/sub_channel_preview").subChannelPreviewOnClickType>["type"]}
     */
    openLinkedSubChannel(ev, { channelAtRender }) {
        channelAtRender.open();
    },
});
