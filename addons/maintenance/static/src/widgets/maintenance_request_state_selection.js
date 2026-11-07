import { useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { StateSelectionField, stateSelectionField } from "@web/views/fields/state_selection/state_selection_field";

export class MaintenanceRequestStateSelection extends StateSelectionField {
    static template = "maintenance.MaintenanceRequestStateSelection";

    props = useProps({
        ...standardFieldProps,
        showLabel: t.boolean().optional(true),
        withCommand: t.boolean().optional(),
        viewType: t.string().optional(),
    });

    setup() {
        super.setup();
        this.uiService = useService("ui");
        this.icons = {
            normal: "circle",
            changes_requested: "circle",
            approved: "circle",
            done: "check_circle",
            cancelled: "cancel",
        };
        this.classIcons = {
            changes_requested: "oi-filled",
            done: "oi-filled",
            approved: "oi-filled",
            cancelled: "oi-filled",
        };
        this.colorIcons = {
            normal: "text-muted",
            changes_requested: "o_status_warning",
            approved: "text-success",
            done: "o_status_success",
            cancelled: "o_status_danger",
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

    stateIconClass(value) {
        return this.classIcons[value] || "";
    }

    statusColor(value) {
        return this.colorIcons[value] || "";
    }

    get options() {
        const labels = new Map(super.options);
        return ["normal", "changes_requested", "approved", "cancelled", "done"].map((state) => [state, labels.get(state)]);
    }

    get isKanbanOrMobileView() {
        return this.props.viewType === "card" || this.uiService.isSmall;
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
