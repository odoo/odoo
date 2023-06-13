/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

class LineOpenMoveWidget extends Many2OneField {
    async openAction() {
        this.action.doActionButton({
            type: "object",
            resId: this.props.value[0],
            name: "action_open_business_doc",
            resModel: "account.move.line",
        });
    }
}

registry.category("fields").add("line_open_move_widget", LineOpenMoveWidget);
