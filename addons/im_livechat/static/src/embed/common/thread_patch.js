import { Thread } from "@mail/core/common/thread";

import { useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { isEmbedLivechatEnabled } from "./misc";

patch(Thread.prototype, {
    setup() {
        super.setup();
        if (isEmbedLivechatEnabled(this.env)) {
            this.chatbotService = useState(useService("im_livechat.chatbot"));
        }
    },
});
