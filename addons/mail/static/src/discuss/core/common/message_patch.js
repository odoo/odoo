import { Message } from "@mail/core/common/message";
import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";

import { patch } from "@web/core/utils/patch";

Message.components = { ...Message.components, MessageSeenIndicator };

/** @type {Message} */
const messagePatch = {
    get showSeenIndicator() {
        return this.props.message.isSelfAuthored && this.props.thread?.hasSeenFeature;
    },
};
patch(Message.prototype, messagePatch);
