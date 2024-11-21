import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

/** @type {Message} */
const messagePatch = {
    get showSeenIndicator() {
        return this.props.message.isSelfAuthored && this.props.thread?.hasSeenFeature;
    },
};
patch(Message.prototype, messagePatch);
