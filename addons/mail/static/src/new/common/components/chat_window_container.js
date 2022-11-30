/** @odoo-module **/

import { Component } from "@odoo/owl";

import { ChatWindow } from "@mail/new/common/components/chat_window";
import { useMessaging } from "@mail/new/messaging_hook";

export class ChatWindowContainer extends Component {
    setup() {
        this.messaging = useMessaging();
    }

    get chatWindows() {
        return this.messaging.state.discuss.isActive ? [] : this.messaging.state.chatWindows;
    }
}

Object.assign(ChatWindowContainer, {
    components: { ChatWindow },
    props: [],
    template: "mail.chat_window_container",
});
