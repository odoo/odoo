import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class ActivityCountsField extends Component {
    static props = { ...standardFieldProps };
    static template = "base.ActivityCountsField";
}

registry.category("fields").add("activity_counts_field", {
    component: ActivityCountsField,
});
