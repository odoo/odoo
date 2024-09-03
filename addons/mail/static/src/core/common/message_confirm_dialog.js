import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { discussComponentRegistry } from "./discuss_component_registry";

export class MessageConfirmDialog extends Component {
    static components = { Dialog };
    static props = [
        "close",
        "confirmColor?",
        "confirmText?",
        "message",
        "prompt",
        "size?",
        "title?",
        "onConfirm",
    ];
    static defaultProps = {
        confirmColor: "btn-primary",
        confirmText: _t("Delete"),
        size: "xl",
        title: _t("Not proud of your message?"),
    };
    static template = "mail.MessageConfirmDialog";

    get messageComponent() {
        return discussComponentRegistry.get("Message");
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}

discussComponentRegistry.add("MessageConfirmDialog", MessageConfirmDialog);
