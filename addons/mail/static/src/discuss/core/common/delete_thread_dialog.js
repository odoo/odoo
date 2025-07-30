import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class DeleteThreadDialog extends Component {
    static components = { ActionPanel };
    static props = ["thread", "close"];
    static template = "discuss.DeleteThreadDialog";

    async onConfirmation() {
        await rpc("/discuss/channel/sub_channel/delete", {
            sub_channel_id: this.props.thread.id,
        });
        this.props.close();
        this.env.services.notification.add(
            `"${this.props.thread.name}" ${_t("thread was deleted")}`,
            {
                type: "warning",
            }
        );
    }

    get warningMessage() {
        return _t("Permanently delete this thread?");
    }
}
