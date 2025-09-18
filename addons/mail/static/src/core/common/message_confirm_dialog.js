import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/ui/dialog/dialog";

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
        title: _t("Send this message to the great trash can in the sky?"),
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
