import { Dialog } from "@web/core/dialog/dialog";

export class CloseAllConfirmation extends Dialog {
    static template = "mail.CloseAllConfirmation";
    static components = { Dialog };
    static props = {
        ...Dialog.props,
        message: { type: String },
        close: { type: Function },
        onConfirm: { type: Function },
        slots: { optional: true },
    };

    onClickConfirm() {
        if (this.props.onConfirm) {
            this.props.onConfirm();
        }
        this.dismiss();
    }
}
