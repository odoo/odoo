/** @odoo-module */

import { useStore } from "@mail/core/messaging_hook";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { SESSION_STATE } from "@im_livechat/new/core/livechat_service";

export class LivechatButton extends Component {
    static template = "im_livechat.LivechatButton";
    static OPEN_CHAT_DEBOUNCE = 500;

    setup() {
        this.store = useStore();
        this.chatWindowService = useService("mail.chat_window");
        this.livechatService = useState(useService("im_livechat.livechat"));
        this.threadService = useService("mail.thread");
        this.onClick = debounce(this.onClick.bind(this), LivechatButton.OPEN_CHAT_DEBOUNCE, {
            leading: true,
        });
    }

    onClick() {
        this.livechatService.sessionState;
        this.threadService.openChat();
    }

    get isShown() {
        return (
            this.livechatService.available &&
            this.livechatService.state !== SESSION_STATE.CLOSED &&
            this.store.chatWindows.length === 0
        );
    }
}
