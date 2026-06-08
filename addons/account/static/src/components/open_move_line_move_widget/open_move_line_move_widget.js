import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

class LineOpenMoveWidget extends Component {
    static template = "account.LineOpenMoveWidget";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.action = useService("action");
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            openRecordAction: () => this.openAction(),
        };
    }

    async openAction() {
        return this.action.doActionButton({
            type: "object",
            resId: this.props.record.data[this.props.name].id,
            name: "action_open_business_doc",
            resModel: "account.move.line",
        });
    }
}

registry.category("fields").add("line_open_move_widget", {
    ...buildM2OFieldDescription(LineOpenMoveWidget),
});
