import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get shouldHideFromMessageListOnDelete() {
        return true;
    },
});
