/** @odoo-module */

import { Thread } from "../thread/thread";
import { Composer } from "../composer/composer";
import { useMessaging } from "../messaging_hook";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CallUI } from "../rtc/call_ui";

export class ChatWindow extends Component {
    setup() {
        this.messaging = useMessaging();
        this.state = useState({ folded: false });
        this.action = useService("action");
    }

    close() {
        this.messaging.closeChatWindow(this.props.threadId);
    }

    toggleFold() {
        this.state.folded = !this.state.folded;
    }

    expand() {
        // todo
        this.messaging.setDiscussThread(this.props.threadId);
        this.action.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            { clearBreadcrumbs: true }
        );
    }

    startCall() {
        this.messaging.startCall(this.props.threadId);
    }
}

Object.assign(ChatWindow, {
    components: { Thread, Composer, CallUI },
    props: ["threadId", "right?", "autofocus?"],
    template: "mail.chat_window",
});
