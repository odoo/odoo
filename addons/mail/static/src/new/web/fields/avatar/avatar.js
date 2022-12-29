/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useOpenChat } from "@mail/new/web/open_chat_hook";

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
