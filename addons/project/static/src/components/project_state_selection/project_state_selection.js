import { registry } from "@web/core/registry";
import {
    StateSelectionField,
    stateSelectionField,
} from "@web/views/fields/state_selection/state_selection_field";

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from "../../utils/project_utils";

export class ProjectStateSelectionField extends StateSelectionField {
    static template = "project.ProjectStateSelection";

    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
        this.icons = {
            at_risk: "priority_high",
            off_track: "cancel",
            on_hold: "pause_circle",
            done: "check_circle",
        };
        this.classIcons = {
            at_risk: "oi oi-filled o_status",
            off_track: "oi oi-filled",
            on_hold: "oi oi-filled",
            done: "oi oi-filled",
        };
        this.colorIcons = {
            at_risk: "o_status_changes_requested",
            off_track: "text-danger",
            on_hold: "text-info",
            done: "text-primary",
        };
    }

    /**
     * @override
     */
    get options() {
        return super.options.filter((o) => o[0] !== "to_define");
    }

    /**
     * @override
     */
    statusColor(value) {
        return this.colorIcons[value] || super.statusColor(value);
    }

    stateIcon(value) {
        return this.icons[value] || "";
    }

    stateClassIcon(value) {
        return this.classIcons[value] || "";
    }
}

export const projectStateSelectionField = {
    ...stateSelectionField,
    component: ProjectStateSelectionField,
};

registry.category("fields").add("project_state_selection", projectStateSelectionField);
