/* @odoo-module */

import { useOpenChat } from "@mail/core/web/open_chat_hook";

import { Component } from "@odoo/owl";

export class Avatar extends Component {
    setup() {
        this.openChat = useOpenChat(this.props.resModel);
    }

    onClickAvatar() {
        this.openChat(this.props.resId);
    }
}
Avatar.template = "mail.Avatar";
Avatar.props = ["resModel", "resId", "displayName"];
