/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class OpenMoveWidget extends Component {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async openMove(ev) {
        this.action.doActionButton({
            type: "object",
            resId: this.props.record.resId,
            name: "action_open_business_doc",
            resModel: "account.move.line",
        });
    }
}

OpenMoveWidget.template = "account.OpenMoveWidget";
registry.category("fields").add("open_move_widget", OpenMoveWidget);
