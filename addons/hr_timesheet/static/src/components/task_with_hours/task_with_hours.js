import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class TaskWithHours extends Component {
    static template = "hr_timesheet.TaskWithHours";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get canCreateTask() {
        return Boolean(this.props.context.default_project_id);
    }

    get m2oProps() {
        const props = this.m2o.computeProps();
        return {
            ...props,
            canCreate: props.canCreate && this.canCreateTask,
            canCreateEdit: props.canCreateEdit && this.canCreateTask,
            canQuickCreate: props.canQuickCreate && this.canCreateTask,
            context: { ...props.context, hr_timesheet_display_remaining_hours: true },
            value: props.value && [props.value[0], props.value[1]?.split("\u00A0")[0]],
        };
    }
}

registry.category("fields").add("task_with_hours", {
    ...buildM2OFieldDescription(TaskWithHours),
});
