import { useOpenChat } from "@mail/core/web/open_chat_hook";

import { Component } from "@odoo/owl";

export class Avatar extends Component {
    static template = "mail.Avatar";
    static props = {
        resModel: { type: String, optional: true },
        resId: { type: Number, optional: true },
        displayName: { type: String, optional: true },
        noSpacing: { type: Boolean, optional: true },
    };

    setup() {
        if (this.props.resModel === "res.users") {
            this.openChat = useOpenChat(this.props.resModel);
        }
    }

    onClickAvatar() {
        if (this.props.resModel === "res.users") {
            this.openChat(this.props.resId);
        }
    }
}
