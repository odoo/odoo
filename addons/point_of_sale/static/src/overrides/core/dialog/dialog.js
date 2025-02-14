import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

patch(Dialog, {
    props: {
        ...Dialog.props,
        subtitle: { type: String, optional: true },
    },
});
