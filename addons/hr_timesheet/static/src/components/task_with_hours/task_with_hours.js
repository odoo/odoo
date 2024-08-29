/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

class TaskWithHours extends Many2OneField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.createEditProject = await this.orm.call(
            "project.project",
            "get_create_edit_project_ids",
            []
        );
    }

    canCreate() {
        if (this.createEditProject !== undefined) {
            return (
                Boolean(this.context.default_project_id) &&
                !this.createEditProject.includes(this.props.record.data.project_id[0])
            );
        } else {
            return Boolean(this.context.default_project_id);
        }
    }

    /**
     * @override
     */
    get displayName() {
        const displayName = super.displayName;
        return displayName ? displayName.split('\u00A0')[0] : displayName;
    }

    /**
     * @override
     */
    get context() {
        return {...super.context, hr_timesheet_display_remaining_hours: true};
    }

    /**
     * @override
     */
    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        if (!this.canCreate()) {
            props.quickCreate = null;
        }
        return props;
    }

    /**
     * @override
     */
    computeActiveActions(props) {
        super.computeActiveActions(props);
        const activeActions = this.state.activeActions;
        activeActions.create = activeActions.create && this.canCreate(props);
        activeActions.createEdit = activeActions.createEdit && this.canCreate(props);
    }

}

registry.category("fields").add("task_with_hours", {
    ...many2OneField,
    component: TaskWithHours,
});
