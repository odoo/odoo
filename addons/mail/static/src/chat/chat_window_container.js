/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useMessaging } from "../messaging_hook";
import { ChatWindow } from "./chat_window";

export class ChatWindowContainer extends Component {
    static template = "mail.chat_window_container";
    static components = { ChatWindow };
    static props = [];

    setup() {
        this.messaging = useMessaging();
    }

    get chatWindows() {
        return this.messaging.discuss.isActive ? [] : this.messaging.chatWindows;
    }
}

registry.category("main_components").add("mail.ChatWindowContainer", {
    Component: ChatWindowContainer,
});
