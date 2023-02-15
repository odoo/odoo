/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

class LineOpenMoveWidget extends Many2OneField {
    async openAction() {
        const action = await this.orm.call("account.move.line", "action_open_business_doc", [this.props.value[0]], {});
        await this.action.doAction(action);
    }
}

registry.category("fields").add("line_open_move_widget", LineOpenMoveWidget);
