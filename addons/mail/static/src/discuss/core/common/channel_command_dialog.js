import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, props, signal, t } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useAutofocus, useService } from "@web/core/utils/hooks";

const commandRegistry = registry.category("discuss.channel_commands");

export class ChannelCommandDialog extends Component {
    static template = "mail.ChannelCommandDialog";
    static components = { ActionPanel };

    setup() {
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class),
            close: t.function([]),
            commandName: t.string(),
            placeholderText: t.string(),
            title: t.string(),
            icon: t.string(),
        });
        this.inputText = signal("");
        this.inputRef = signal.ref(HTMLInputElement);
        useAutofocus({ ref: this.inputRef });
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && this.inputText().trim().length > 0) {
            this.executeCommand();
        }
    }

    executeCommand() {
        const command = commandRegistry.get(this.props.commandName, false);
        if (command) {
            this.props.channel.executeCommand(
                command,
                `/${this.props.commandName} ${this.inputText()}`
            );
            this.props.close();
        }
    }
}
