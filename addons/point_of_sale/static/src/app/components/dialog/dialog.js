import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

patch(Dialog, {
    props: {
        ...Dialog.props,
        backdrop: { type: Boolean, optional: true },
        closeOnBodyButtonClick: { type: Boolean, optional: true },
    },
    defaultProps: { ...Dialog.defaultProps, backdrop: false, closeOnBodyButtonClick: false },
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
