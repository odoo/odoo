import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";

import { Component } from "@odoo/owl";

export class ThreadPreview extends Component {
    static components = { MessageSeenIndicator };
    static props = ["channel", "className?", "close"];
    static defaultProps = {
        className: "",
    };
    static template = "mail.ThreadPreview";

    get message() {
        return this.props.channel?.newestPersistentOfAllMessage;
    }

    get previewText() {
        return this.message?.previewText;
    }
}
