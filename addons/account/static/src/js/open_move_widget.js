/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField } from "@web/views/fields/char/char_field";

class OpenMoveWidget extends CharField{
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async _onOpenMove(ev) {
        const act = await this.orm.call("account.move.line", "open_move", [this.props.record.resId], {})
        this.action.doAction(act);
    }
}

OpenMoveWidget.template = "account.OpenMoveWidget";
registry.category("fields").add("open_move_widget", OpenMoveWidget);
