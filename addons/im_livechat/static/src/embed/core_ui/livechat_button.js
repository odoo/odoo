/** @odoo-module */

import { useStore } from "@mail/core/messaging_hook";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { SESSION_STATE } from "@im_livechat/embed/core/livechat_service";

export class LivechatButton extends Component {
    static template = "im_livechat.LivechatButton";

    setup() {
        this.store = useStore();
        this.chatWindowService = useService("mail.chat_window");
        this.livechatService = useState(useService("im_livechat.livechat"));
        this.threadService = useService("mail.thread");
        this.onClick = debounce(this.onClick.bind(this), 500, { leading: true });
    }

    onClick() {
        this.threadService.openChat();
    }

    get isShown() {
        return (
            this.livechatService.initialized &&
            this.livechatService.available &&
            !this.livechatService.shouldRestoreSession &&
            this.livechatService.state !== SESSION_STATE.CLOSED &&
            this.store.chatWindows.length === 0
        );
    }

    get text() {
        return this.livechatService.options.button_text;
    }
}
