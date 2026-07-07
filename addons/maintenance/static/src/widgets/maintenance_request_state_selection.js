import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { StateSelectionField, stateSelectionField } from "@web/views/fields/state_selection/state_selection_field";

export class MaintenanceRequestStateSelection extends StateSelectionField {
    static template = "maintenance.MaintenanceRequestStateSelection";

    props = props({
        ...standardFieldProps,
        showLabel: t.boolean().optional(true),
        withCommand: t.boolean().optional(),
        viewType: t.string().optional(),
    });

    setup() {
        super.setup();
        this.uiService = useService("ui");
        this.icons = {
            normal: "o_status",
            changes_requested: "fa fa-lg fa-exclamation-circle",
            approved: "o_status o_status_green",
            done: "fa fa-lg fa-check-circle",
            cancelled: "fa fa-lg fa-times-circle",
        };
        this.colorIcons = {
            normal: "",
            changes_requested: "o_status_changes_requested",
            approved: "text-success",
            done: "text-success",
            cancelled: "text-danger",
        };
        this.colorButton = {
            normal: "btn-outline-secondary",
            changes_requested: "btn-outline-warning",
            approved: "btn-outline-success",
            done: "btn-outline-success",
            cancelled: "btn-outline-danger",
        };
    }

    stateIcon(value) {
        return this.icons[value] || "";
    }

    statusColor(value) {
        return this.colorIcons[value] || "";
    }

    get options() {
        const labels = new Map(super.options);
        return ["normal", "changes_requested", "approved", "cancelled", "done"].map((state) => [state, labels.get(state)]);
    }

    get isKanbanOrMobileView() {
        return this.props.viewType === "kanban" || this.uiService.isSmall;
    }

    getTogglerClass(currentValue) {
        return this.isKanbanOrMobileView ? "p-0" : `o_state_button btn rounded-pill ${this.colorButton[currentValue]}`;
    }
}

export const maintenanceRequestStateSelectionField = {
    ...stateSelectionField,
    component: MaintenanceRequestStateSelection,
    extractProps({ viewType }) {
        const props = stateSelectionField.extractProps(...arguments);
        props.viewType = viewType;
        return props;
    },
};

registry.category("fields").add("maintenance_request_state_selection", maintenanceRequestStateSelectionField);
