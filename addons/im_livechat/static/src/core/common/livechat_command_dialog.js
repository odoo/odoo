import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, proxy, signal, t, useProps } from "@odoo/owl";

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

export class LivechatCommandDialog extends Component {
    static template = "im_livechat.LivechatCommandDialog";
    static components = { ActionPanel };
    props = useProps({
        thread: t.object(),
        close: t.function(),
        commandName: t.string(),
        placeholderText: t.string(),
        title: t.string(),
        icon: t.string(),
    });

    autofocusRef = signal.ref();

    setup() {
        this.state = proxy({ inputText: "" });
        this.store = useService("mail.store");
        useAutofocus({ ref: this.autofocusRef });
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && this.state.inputText.trim().length > 0) {
            this.executeCommand();
        }
    }

    executeCommand() {
        const command = commandRegistry.get(this.props.commandName, false);
        if (command) {
            this.props.thread.channel.executeCommand(
                command,
                `/${this.props.commandName} ${this.state.inputText}`
            );
            this.props.close();
        }
    }
}
