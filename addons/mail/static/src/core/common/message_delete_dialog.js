import { discussComponentRegistry } from "./discuss_component_registry";

import { Component, props, types } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class MessageDeleteDialog extends Component {
    static components = { Dialog };
    static template = "mail.MessageDeleteDialog";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            close: types.function([types.instanceOf(MouseEvent)]),
            message: types.instanceOf(this.store["mail.message"].Class),
            onConfirm: types.function([]),
        });
    }

    get messageComponent() {
        return discussComponentRegistry.get("Message");
    }

    onClickConfirm() {
        this.props.onConfirm();
        this.props.close();
    }
}

discussComponentRegistry.add("MessageDeleteDialog", MessageDeleteDialog);
