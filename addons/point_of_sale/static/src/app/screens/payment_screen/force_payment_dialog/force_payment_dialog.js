import {
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { t, untrack, useEffect, useProps } from "@odoo/owl";

export class ForcePaymentDialog extends ConfirmationDialog {
    props = useProps({ ...confirmationDialogProps, line: t.object() });

    setup() {
        super.setup();
        useEffect(() => {
            if (["done", "retry"].includes(this.props.line.payment_status)) {
                untrack(() => this.props.close());
            }
        });
    }
}
