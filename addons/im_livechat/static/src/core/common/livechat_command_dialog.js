import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, useState } from "@odoo/owl";

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

export class LivechatCommandDialog extends Component {
    static template = "im_livechat.LivechatCommandDialog";
    static components = { ActionPanel };
    static props = ["thread", "close", "commandName", "placeholderText", "title", "icon"];

    setup() {
        this.state = useState({ inputText: "" });
        this.store = useService("mail.store");
        useAutofocus();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && this.state.inputText.trim().length > 0) {
            this.executeCommand();
        }
    }

    executeCommand() {
        const command = commandRegistry.get(this.props.commandName, false);
        if (command) {
            this.props.thread.executeCommand(
                command,
                `/${this.props.commandName} ${this.state.inputText}`
            );
            this.props.close();
        }
    }
}
