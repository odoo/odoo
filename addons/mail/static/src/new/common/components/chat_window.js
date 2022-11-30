/** @odoo-module */

import { Thread } from "../../thread/thread";
import { Composer } from "@mail/new/common/components/composer";
import { useMessageHighlight, useMessaging } from "@mail/new/messaging_hook";
import { Component, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CallUI } from "@mail/new/discuss/components/call_ui";
import { CallSettings } from "@mail/new/discuss/components/call_settings";

export class ChatWindow extends Component {
    setup() {
        this.messaging = useMessaging();
        this.messageHighlight = useMessageHighlight();
        this.state = useState({
            inSettings: false,
        });
        this.action = useService("action");
        this.contentRef = useRef("content");
        useChildSubEnv({ inChatWindow: true });
    }

    close() {
        this.messaging.closeChatWindow(this.props.chatWindow.threadId);
    }

    toggleFold() {
        this.props.chatWindow.folded = !this.props.chatWindow.folded;
    }

    toggleSettings() {
        this.state.inSettings = !this.state.inSettings;
    }

    expand() {
        this.messaging.setDiscussThread(this.props.chatWindow.threadId);
        this.action.doAction(
            {
                type: "ir.actions.client",
                tag: "mail.action_discuss",
            },
            { clearBreadcrumbs: true }
        );
    }

    startCall() {
        this.messaging.startCall(this.props.chatWindow.threadId);
    }
}

Object.assign(ChatWindow, {
    components: { Thread, Composer, CallUI, CallSettings },
    props: ["chatWindow", "right?"],
    template: "mail.chat_window",
});
