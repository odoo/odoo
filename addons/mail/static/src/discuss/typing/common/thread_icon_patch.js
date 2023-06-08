/* @odoo-module */

import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useTypingService } from "@mail/discuss/typing/common/typing_service";

import { patch } from "@web/core/utils/patch";

patch(ThreadIcon, "discuss/typing/common", {
    components: { ...ThreadIcon.components, Typing },
});

patch(ThreadIcon.prototype, "discuss/typing/common", {
    /**
     * @override
     */
    setup() {
        this._super();
        this.typingService = useTypingService();
    },
});
