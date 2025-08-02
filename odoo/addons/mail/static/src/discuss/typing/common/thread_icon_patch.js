/* @odoo-module */

import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { patch } from "@web/core/utils/patch";

patch(ThreadIcon, {
    components: { ...ThreadIcon.components, Typing },
});

patch(ThreadIcon.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.typingService = useState(useService("discuss.typing"));
    },
});
