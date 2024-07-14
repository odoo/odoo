/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class AddressRecurrencyConfirmationDialog extends ConfirmationDialog {
    static template = "planning.AddressRecurrencyConfirmationDialog";
    static props = {
        ...ConfirmationDialog.props,
        body: { type: String, optional: true },
        onChangeRecurrenceUpdate: { type: Function },
        selected: { type: String },
    };
    static defaultProps = {
        ...ConfirmationDialog.defaultProps,
        body: "",
        cancel: () => {},
        title: _t("Delete Recurring Shift")
    };
}
