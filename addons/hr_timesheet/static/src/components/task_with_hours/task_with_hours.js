import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Component, onWillStart } from "@odoo/owl";

export class TaskWithHours extends Component {
    static template = "hr_timesheet.TaskWithHours";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        super.setup();
        onWillStart(this.onWillStart);
    }

    async onWillStart() { }

    canCreate() {
        return Boolean(this.props.context.default_project_id);
    }

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            canCreate: props.canCreate && this.canCreate(),
            canCreateEdit: props.canCreateEdit && this.canCreate(),
            canQuickCreate: props.canQuickCreate && this.canCreate(),
            context: { ...props.context, hr_timesheet_display_remaining_hours: true },
            value: props.value && {
                ...props.value,
                display_name: props.value.display_name?.split("\u00A0")[0],
            },
        };
    }
}

registry.category("fields").add("task_with_hours", {
    ...buildM2OFieldDescription(TaskWithHours),
});
