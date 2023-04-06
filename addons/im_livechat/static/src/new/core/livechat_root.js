/** @odoo-module */

import { ChatWindowContainer } from "@mail/web/chat_window/chat_window_container";
import { Component, xml } from "@odoo/owl";
import { LivechatButton } from "../core_ui/livechat_button";

export class LivechatRoot extends Component {
    static template = xml`
        <ChatWindowContainer/>
        <LivechatButton/>
    `;
    static components = { ChatWindowContainer, LivechatButton };
}
