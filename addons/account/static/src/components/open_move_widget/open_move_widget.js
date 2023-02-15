/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class OpenMoveWidget extends Component {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async openMove(ev) {
        const action = await this.orm.call("account.move.line", "action_open_business_doc", [this.props.record.resId], {});
        this.action.doAction(action);
    }
}

OpenMoveWidget.template = "account.OpenMoveWidget";
registry.category("fields").add("open_move_widget", OpenMoveWidget);
