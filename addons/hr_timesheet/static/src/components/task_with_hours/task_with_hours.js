/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";


class TaskWithHours extends Many2OneField {

    setup() {
        super.setup();
        const activeActions = this.state.activeActions;
        activeActions.canCreate = activeActions.canCreate && this.canCreate;
        activeActions.canQuickCreate = activeActions.canQuickCreate || this.canCreate;
        activeActions.canCreateEdit = activeActions.canCreate;
    }

    get canCreate() {
        return Boolean(this.context.default_project_id);
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
        if (!this.canCreate) {
            props.quickCreate = null;
        }
        return props;
    }

}

registry.category("fields").add("task_with_hours", TaskWithHours);
