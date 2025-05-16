import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, useState } from "@odoo/owl";

import { useAutofocus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";

export class DeleteThreadDialog extends Component {
    static components = { ActionPanel };
    static props = ["thread", "close"];
    static template = "discuss.DeleteThreadDialog";

    setup() {
        super.setup();
        this.state = useState({ confirmationText: "" });
        useAutofocus();
    }

    onKeydown(ev) {
        if (getActiveHotkey(ev) === "enter" && this.state.confirmationText.trim() === "delete") {
            this.onConfirmation();
        }
    }

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

    onCancel() {
        this.props.close();
    }
}
