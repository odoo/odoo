import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class PosConfirmationDialog extends ConfirmationDialog {
    static template = "point_of_sale.PosConfirmationDialog";
    static props = {
        ...ConfirmationDialog.props,
        hideCloseButton: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...ConfirmationDialog.defaultProps,
        hideCloseButton: false,
    };
    setup() {
        useHotkey("escape", () => {});
    }
}
