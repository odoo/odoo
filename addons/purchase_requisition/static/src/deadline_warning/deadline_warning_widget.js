import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useProps } from "@odoo/owl";

export class DeadlineWarningWidget extends Component {
    static template = "purchase_requisition.DeadlineWarningWidget";
    props = useProps({
        ...standardFieldProps,
    });

    get showWarning() {
        return Boolean(this.props.value);
    }

    get getWarningMessage() {
        console.log(this.props.record.data[this.props.name])
        return this.props.record.data[this.props.name];
    }}


registry.category("fields").add("deadline_warning_widget", {
    component: DeadlineWarningWidget,
});