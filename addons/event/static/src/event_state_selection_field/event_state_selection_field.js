import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatSelection } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { StateSelectionField, stateSelectionField } from "@web/views/fields/state_selection/state_selection_field";
import { useService } from "@web/core/utils/hooks";


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
        // Only show the confirmation dialog if the user is trying to cancel the event and it's not already cancelled.
        if (value !== 'cancel' || this.currentValue === 'cancel') {
            return super.updateRecord(value);
        }

        this.dialog.add(ConfirmationDialog, {
            title: _t("Are you sure you want to cancel this event?"),
            body: _t("Any scheduled communication will be blocked.\n\nDon't forget to notify attendees who already registered."),
            confirmLabel: _t("Proceed"),
            confirm: async () => {
                await this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
            },
            cancelLabel: _t("Go back"),
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
