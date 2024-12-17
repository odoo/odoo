import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

class LineOpenMoveWidget extends Component {
    static template = "account.LineOpenMoveWidget";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            openRecordAction: () => this.openAction(),
        };
    }

    openAction() {
        return this.action.doActionButton({
            type: "object",
            resId: this.m2o.resId,
            name: "action_open_business_doc",
            resModel: "account.move.line",
        });
    }
}

registry.category("fields").add("line_open_move_widget", {
    ...buildM2OFieldDescription(LineOpenMoveWidget),
});
