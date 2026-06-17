import { t } from "@odoo/owl";
import { Dialog, dialogProps } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

Object.assign(dialogProps, {
    backdrop: t.boolean().optional(false),
    closeOnBodyButtonClick: t.boolean().optional(false),
});

patch(Dialog.prototype, {
    onClick(event) {
        // Click outside the modal content
        if (this.props.backdrop && event.target === this.modalRef.el) {
            this.dismiss();
        }
        // Click on a button inside the modal body or on an element with the 'close-dialog' class
        else if (
            (this.props.closeOnBodyButtonClick &&
                event.target.closest(".modal-body button:not(.prevent-close-dialog)")) ||
            event.target.closest(".close-dialog")
        ) {
            this.data.close();
        }
    },
});
