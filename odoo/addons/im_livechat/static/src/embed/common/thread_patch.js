/* @odoo-module */

import { Thread } from "@mail/core/common/thread";

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.chatbotService = useState(useService("im_livechat.chatbot"));
    },
});
