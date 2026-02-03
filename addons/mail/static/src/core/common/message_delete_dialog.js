import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { discussComponentRegistry } from "./discuss_component_registry";

export class MessageDeleteDialog extends Component {
    static components = { Dialog };
    static props = {
        close: Function,
        message: Object,
        onConfirm: Function,
    };
    static template = "mail.MessageDeleteDialog";

    get messageComponent() {
        return discussComponentRegistry.get("Message");
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}

discussComponentRegistry.add("MessageDeleteDialog", MessageDeleteDialog);
