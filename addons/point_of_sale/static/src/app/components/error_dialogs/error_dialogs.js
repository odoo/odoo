import { WarningDialog } from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";

patch(WarningDialog, {
    props: {
        ...WarningDialog.props,
        backdrop: { type: Boolean, optional: true },
    },
    defaultProps: { ...WarningDialog.defaultProps, backdrop: false },
});
