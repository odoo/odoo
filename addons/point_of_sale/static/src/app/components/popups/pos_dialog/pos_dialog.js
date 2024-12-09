import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

patch(Dialog, {
    props: {
        ...Dialog.props,
        hideCloseButton: { type: Boolean, optional: true },
    },
    defaultProps: {
        ...Dialog.defaultProps,
        hideCloseButton: false,
    },
});
