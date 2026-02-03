/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class WorkEntryWarnings extends Component {
    static template = "hr_work_entry_enterprise.WorkEntryWarnings";
    static props = { ...standardFieldProps };

    setup() {
        this.actionService = useService("action");
    }

    async onActionClick(action) {
        if (!action) return;
        await this.actionService.doAction(action, {
            onClose: () => this.env.model.load(),
        });
    }

    get issues() {
        const value = this.props.record.data[this.props.name];
        return value ? Object.values(value) : [];
    }
}

export const workEntryWarnings = {
    component: WorkEntryWarnings,
};

registry.category("fields").add("work_entry_warnings", workEntryWarnings);