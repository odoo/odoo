import { formatSelection } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { StateSelectionField, stateSelectionField } from "@web/views/fields/state_selection/state_selection_field";
import { useService } from "@web/core/utils/hooks";


/**
 * This widget is used to enhance the Event State Selection field UI.
 * It extends `StateSelectionField` to provide visual feedback using icons
 * and color classes for different states: `normal`, `done`, `blocked`, `cancel`.
 */
export class EventStateSelection extends StateSelectionField {
    static template = "event.EventStateSelection";

    setup() {
        this.dialog = useService("dialog");
        this.icons = {
            normal: "o_status",
            done: "o_status o_status_green",
            blocked: "fa fa-lg fa-exclamation-circle",
            cancel: "fa fa-lg fa-times-circle",
        };
        this.colorIcons = {
            normal: "",
            done: "text-success",
            blocked: "o_status_blocked",
            cancel: "text-danger",
        };
    }

    get options() {
        return ["normal", "done", "blocked", "cancel"].map((state) => [state, new Map(super.options).get(state)]);
    }

    get label() {
        return formatSelection(this.currentValue, { selection: this.options });
    }

    stateIcon(value) {
        return this.icons[value] || "";
    }

    /**
     * @override
     */
    statusColor(value) {
        return this.colorIcons[value] || "";
    }
}

export const EventStateSelectionField = {
    ...stateSelectionField,
    component: EventStateSelection,
    supportedOptions: [
        ...stateSelectionField.supportedOptions
    ]
}

registry.category("fields").add("event_state_selection", EventStateSelectionField);
