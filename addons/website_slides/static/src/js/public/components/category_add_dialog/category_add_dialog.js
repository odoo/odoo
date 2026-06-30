import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useAutofocus } from "@web/core/utils/hooks";

export class CategoryAddDialog extends ConfirmationDialog {
    static template = "website_slides.CategoryAddDialog";
    static props = {
        ...ConfirmationDialog.props,
        channelId: String,
    };

    setup() {
        super.setup();
        this.inputRef = useAutofocus();
        this.csrf_token = odoo.csrf_token;
        this.lastInputValue;
    }

    _confirm() {
        this.execButton(() => {
            if (this.inputRef.el.value === this.lastInputValue) {
                return;
            }
            this.lastInputValue = this.inputRef.el.value;
            return this.props.confirm({ formEl: this.modalRef.el.querySelector("form") });
        });
    }
}
