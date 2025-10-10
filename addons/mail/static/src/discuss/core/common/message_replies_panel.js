import { Component, onMounted, onWillUpdateProps, useChildSubEnv } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useService } from "@web/core/utils/hooks";
import { MessageCardList } from "@mail/core/common/message_card_list";
import { Message } from "@mail/core/common/message";
import { rpc } from "@web/core/network/rpc";

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
        onWillUpdateProps((nextProps) => {
            if (this.props.thread.notEq(nextProps.thread)) {
                this.env.repliesMenu?.close();
            }
            if (this.props.message.notEq(nextProps.message)) {
                this.fetchDecendants();
            }
        });
        useChildSubEnv({
            closeActionPanel: () => this.env.repliesMenu.close(),
            getCurrentThread: () => this.props.thread,
            repliesMenu: {
                message: this.props.message,
                ...this.env.repliesMenu,
            },
        });
        onMounted(this.fetchDecendants);
    }

    fetchDecendants() {
        rpc("/discuss/message/descendants", {
            message_id: this.props.message.id,
        }).then((data) => {
            this.store.insert(data);
        });
    }

    get orderedDescendants() {
        const descendants = [...this.props.message.descendants];
        return descendants.filter((d) => d.res_id).sort((m1, m2) => m1.id - m2.id);
    }
}
