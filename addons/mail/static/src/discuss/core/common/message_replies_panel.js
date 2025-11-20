import { Component, onMounted, onWillUpdateProps, useChildSubEnv, useState } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useService } from "@web/core/utils/hooks";
import { MessageCardList } from "@mail/core/common/message_card_list";
import { Message } from "@mail/core/common/message";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 */
export class MessageRepliesPanel extends Component {
    static template = "mail.MessageRepliesPanel";
    static components = { ActionPanel, MessageCardList, Message };
    static props = ["message", "thread"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.state = useState({ showLoading: false });
        onMounted(() => {
            this.props.message.descendants.fetch();
        });
        onWillUpdateProps(async (nextProps) => {
            if (this.props.thread.notEq(nextProps.thread)) {
                this.env.messageReplies?.close();
            }
            nextProps.message.descendants.fetch();
        });
        useChildSubEnv({
            closeActionPanel: () => this.env.messageReplies.close(),
            getCurrentThread: () => this.props.thread,
            inMessageRepliesPanel: true,
        });
    }

    async fetchDescendants(message) {
        const loadingTimeoutId = setTimeout(() => (this.state.showLoading = true), 1000);
        try {
            await message.descendants.fetch();
        } finally {
            clearTimeout(loadingTimeoutId);
            this.state.showLoading = false;
        }
    }
}
