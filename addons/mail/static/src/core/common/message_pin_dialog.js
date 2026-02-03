import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

import { discussComponentRegistry } from "./discuss_component_registry";

export class MessagePinDialog extends Component {
    static components = { Dialog };
    static props = {
        close: Function,
        message: Object,
        isUnpin: { type: Boolean, optional: true },
    };
    static template = "mail.MessagePinDialog";

    get messageComponent() {
        return discussComponentRegistry.get("Message");
    }

    get title() {
        return this.props.isUnpin ? _t("Unpin Message") : _t("Pin this message?");
    }

    get prompt() {
        if (this.props.isUnpin) {
            return _t("Are you sure you want to unpin this message?");
        }
        const thread = this.props.message.thread;
        return _t("Are you sure you want to pin this message to %(conversation)s?", {
            conversation: thread.prefix + thread.displayName,
        });
    }

    get promptSecondary() {
        return this.props.isUnpin
            ? _t("You can always pin it again later if needed.")
            : _t("It will remain pinned until you decide to remove it.");
    }

    get confirmText() {
        return this.props.isUnpin ? _t("Unpin Message") : _t("Pin Message");
    }

    onClickConfirm() {
        const { message, isUnpin } = this.props;
        message.thread.setMessagePin(message, !isUnpin);
        this.props.close();
    }
}
