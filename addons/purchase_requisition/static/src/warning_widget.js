import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useProps } from "@odoo/owl";

export class WarningWidget extends Component {
    static template = "purchase_requisition.WarningWidget";
    props = useProps({
        ...standardFieldProps,
    });

    get warningMessage() {
        return this.props.record.data[this.props.name];
    }
}

registry.category("fields").add("warning_widget", {
    component: WarningWidget,
});
