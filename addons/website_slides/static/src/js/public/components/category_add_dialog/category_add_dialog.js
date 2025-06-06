import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useAutofocus } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

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
        this.onOutsideClick = (event) => {
            const isInsideDialog = event.target.closest(".modal-content");
            if (!isInsideDialog) {
                this.props.close();
            }
        };
        onMounted(() => {
            document.addEventListener("click", this.onOutsideClick);
        });
        onWillUnmount(() => {
            document.removeEventListener("click", this.onOutsideClick);
        });
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
