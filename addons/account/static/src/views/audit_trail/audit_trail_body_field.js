import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AuditTrailBodyField extends Component {
    static template = "account.AuditTrailBodyField";

    props = useProps(standardFieldProps);

    get isTracking() {
        return this.props.record.data.message_type === "tracking";
    }
}

registry.category("fields").add("audit_trail_body_field", {
    component: AuditTrailBodyField,
    fieldDependencies: [{ name: "message_type", type: "selection" }],
});
