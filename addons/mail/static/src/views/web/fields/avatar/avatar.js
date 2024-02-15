import { useOpenChat } from "@mail/core/web/open_chat_hook";

import { Component } from "@odoo/owl";

export class Avatar extends Component {
    static template = "mail.Avatar";
    static props = {
        resModel: { type: String },
        resId: { type: Number },
        displayName: { type: String },
        noSpacing: { type: Boolean, optional: true },
    };

    setup() {
        this.openChat = useOpenChat(this.props.resModel);
    }

    onClickAvatar() {
        this.openChat(this.props.resId);
    }
}
