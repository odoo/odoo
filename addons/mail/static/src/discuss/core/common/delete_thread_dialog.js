import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class DeleteThreadDialog extends Component {
    static components = { ActionPanel };
    static props = ["thread", "close"];
    static template = "discuss.DeleteThreadDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    async onConfirmation() {
        let toOpenThread;
        const threadName = this.props.thread.name;
        if (this.store.discuss?.thread?.eq(this.props.thread) || this.env.inChatWindow) {
            toOpenThread = this.props.thread.parent_channel_id;
        }
        await rpc("/discuss/channel/sub_channel/delete", {
            sub_channel_id: this.props.thread.id,
        });
        if (toOpenThread?.exists()) {
            toOpenThread.open();
        }
        this.props.close();
        this.env.services.notification.add(
            _t('Thread "%(thread_name)s" has been deleted', { thread_name: threadName }),
            { type: "info" }
        );
    }
}
