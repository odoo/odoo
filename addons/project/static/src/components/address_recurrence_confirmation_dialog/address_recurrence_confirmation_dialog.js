/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class AddressRecurrenceConfirmationDialog extends ConfirmationDialog {
    get title() {
        return this.props.mode === "delete"
             ? this.env._t("Delete Recurring Task")
             : this.env._t("Archive Recurring Task");
    }

    get question() {
        return this.props.mode === "delete"
             ? this.env._t("This task is recurrent. Delete it and...")
             : this.env._t("This task is recurrent. Archive it and...");
    }

    get thisLabel() {
        return this.env._t("continue the recurrence");
    }

    get futureLabel() {
        return this.env._t("stop the recurrence");
    }
}

AddressRecurrenceConfirmationDialog.template = "project.AddressRecurrenceConfirmationDialog";
AddressRecurrenceConfirmationDialog.props = {
    ...ConfirmationDialog.props,
    body: { type: String, optional: true },
    mode: { type: String },
    onChangeRecurrenceUpdate: { type: Function },
};
AddressRecurrenceConfirmationDialog.defaultProps = {
    ...ConfirmationDialog.defaultProps,
    body: "",
    cancel: () => {},
};
