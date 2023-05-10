/* @odoo-module */

import { ThreadIcon } from "@mail/discuss_app/thread_icon";
import { Typing } from "@mail/discuss/typing/typing";
import { useTypingService } from "@mail/discuss/typing/typing_service";
import { patch } from "@web/core/utils/patch";

patch(ThreadIcon, "discuss/typing", {
    components: { ...ThreadIcon.components, Typing },
});

patch(ThreadIcon.prototype, "discuss/typing", {
    /**
     * @override
     */
    setup() {
        this._super();
        this.typingService = useTypingService();
    },
});
