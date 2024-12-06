import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class OpenMoveWidget extends Component {
    static template = "account.OpenMoveWidget";
    static props = { ...standardFieldProps };

    setup() {
        super.setup();
        this.action = useService("action");
    }

    async openMove(ev) {
        this.action.doActionButton({
            type: "object",
            resId: this.props.record.resId,
            name: "action_open_business_doc",
            resModel: this.props.record.resModel,
        });
    }
}

registry.category("fields").add("open_move_widget", {
    component: OpenMoveWidget,
});
