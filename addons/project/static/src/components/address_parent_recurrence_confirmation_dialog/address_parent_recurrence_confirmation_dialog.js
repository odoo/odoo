/** @odoo-module */

import { AddressRecurrenceConfirmationDialog } from "../address_recurrence_confirmation_dialog/address_recurrence_confirmation_dialog";

export class AddressParentRecurrenceConfirmationDialog extends AddressRecurrenceConfirmationDialog {
    get title() {
        return this.props.mode === "delete"
             ? this.env._t("Delete Task")
             : this.env._t("Archive Task");
    }

    get question() {
        return this.props.mode === "delete"
             ? this.env._t("This is a recurring task's child. Delete it and..")
             : this.env._t("This is a recurring task's child. Archive it and..");
    }

    get thisLabel() {
        return this.env._t("keep it in future occurrences");
    }

    get futureLabel() {
        return this.env._t("remove it from future occurrences");
    }
}
