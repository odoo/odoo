import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class OpenMatchLineWidget extends Component {
    static template = "purchase.OpenMatchLineWidget";
    static props = { ...standardFieldProps };

    setup() {
        super.setup();
        this.action = useService("action");
    }

    async openMatchLine() {
        this.action.doActionButton({
            type: "object",
            resId: this.props.record.resId,
            name: "action_open_line",
            resModel: "purchase.bill.line.match",
        });
    }
}

registry.category("fields").add("open_match_line_widget", {
    component: OpenMatchLineWidget,
});
