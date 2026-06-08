import { props, t } from "@odoo/owl";
import {
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SettingsConfirmationDialog extends ConfirmationDialog {
    static template = "web.SettingsConfirmationDialog";
    props = props({
        ...confirmationDialogProps,
        title: t
            .customValidator(
                t.any(),
                (m) =>
                    typeof m === "string" ||
                    (typeof m === "object" && typeof m.toString === "function")
            )
            .optional(_t("Unsaved changes")),
        stayHere: t.function().optional(),
    });

    _stayHere() {
        if (this.props.stayHere) {
            this.props.stayHere();
        }
        this.props.close();
    }
}
