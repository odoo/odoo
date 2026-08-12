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
            normal: "circle",
            done: "check_circle",
            blocked: "circle",
            cancel: "cancel",
        };
        this.classIcons = {
            done: "oi-filled",
            cancel: "oi-filled",
            blocked: "oi-filled",
        };
        this.colorIcons = {
            normal: "text-muted",
            done: "o_status_green",
            blocked: "o_status_orange",
            cancel: "o_status_red",
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

    stateIconClass(value) {
        return this.classIcons[value] || "";
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
