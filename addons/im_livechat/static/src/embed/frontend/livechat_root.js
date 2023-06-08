/* @odoo-module */

import { LivechatButton } from "@im_livechat/embed/core_ui/livechat_button";

import { ChatWindowContainer } from "@mail/core/common/chat_window_container";

import { Component, xml } from "@odoo/owl";

export class LivechatRoot extends Component {
    static template = xml`
        <ChatWindowContainer/>
        <LivechatButton/>
    `;
    static components = { ChatWindowContainer, LivechatButton };
}
