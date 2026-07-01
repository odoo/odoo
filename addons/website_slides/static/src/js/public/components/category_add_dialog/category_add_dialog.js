import { props, signal, t } from "@odoo/owl";
import {
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { useAutofocus } from "@web/core/utils/hooks";

export class CategoryAddDialog extends ConfirmationDialog {
    static template = "website_slides.CategoryAddDialog";
    props = props({
        ...confirmationDialogProps,
        channelId: t.string(),
    });

    inputRef = signal(null);

    setup() {
        super.setup();
        useAutofocus({ ref: this.inputRef });
        this.csrf_token = odoo.csrf_token;
        this.lastInputValue;
    }

    _confirm() {
        this.execButton(() => {
            if (this.inputRef().value === this.lastInputValue) {
                return;
            }
            this.lastInputValue = this.inputRef().value;
            return this.props.confirm({ formEl: this.modalRef.el.querySelector("form") });
        });
    }
}
