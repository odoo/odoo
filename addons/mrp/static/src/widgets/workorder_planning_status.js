import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class WorkorderPlanningStatus extends Component {
    static template = "mrp.WorkorderPlanningStatus";
    static props = { ...standardFieldProps };
}

registry.category("fields").add("workorder_planning_status", {
    component: WorkorderPlanningStatus,
    supportedTypes: ["boolean"],
});
