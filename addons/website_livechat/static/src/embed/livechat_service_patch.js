/* @odoo-module */

import { LivechatService } from "@im_livechat/embed/core/livechat_service";
import { patch } from "@web/core/utils/patch";

patch(LivechatService.prototype, {
    setup(env, services) {
        super.setup(env, services);
        if (this.options?.chat_request_session) {
            this.updateSession(this.options.chat_request_session);
        }
    },

    get displayWelcomeMessage() {
        return (
            (this.thread.messages.length === 0 || this.thread?.messages[0]?.isSelfAuthored) &&
            super.displayWelcomeMessage
        );
    },
});
