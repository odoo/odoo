import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { StateSelectionField, stateSelectionField} from "@web/views/fields/state_selection/state_selection_field";
import { formatSelection } from "@web/views/fields/formatters";

import { registry } from "@web/core/registry";

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

    async updateRecord(value) {
        if (value !== 'cancel' || this.currentValue === 'cancel') {
            return super.updateRecord(value);
        }

        const message = _t(
            "Are you sure you want to cancel this event? If published, the event will remain visible on your website with a cancellation banner. Don't forget to notify your registered attendees."
        );

        this.dialog.add(ConfirmationDialog, {
            title: _t("Warning"),
            body: message,
            confirmLabel: _t("Proceed"),
            confirm: async () => {
                await this.props.record.update(
                    { [this.props.name]: value },
                    { save: this.props.autosave }
                );
            },
            cancel: () => {},
        });
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
