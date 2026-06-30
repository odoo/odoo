import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SettingsConfirmationDialog extends ConfirmationDialog {
    static template = "web.SettingsConfirmationDialog";
    static defaultProps = {
        title: _t("Unsaved changes"),
    };
    static props = {
        ...ConfirmationDialog.props,
        stayHere: { type: Function, optional: true },
    };

    _stayHere() {
        if (this.props.stayHere) {
            this.props.stayHere();
        }
        this.props.close();
    }
}
