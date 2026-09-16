import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class WorkEntryTypeBadgeField extends Component {
    static template = "hr_work_entry.WorkEntryTypeBadgeField";

    props = useProps(standardFieldProps);
}

registry.category("fields").add("work_entry_type_badge", {
    component: WorkEntryTypeBadgeField,
    fieldDependencies: [
        { name: "color", type: "integer" },
        { name: "name", type: "char" },
    ],
});
