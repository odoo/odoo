import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useEffect } from "@odoo/owl";
import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";

patch(FeedbackScreen.prototype, {
    setup() {
        super.setup();
        useEffect(() => {
            if (this.loading() === false) {
                const error = this.currentOrder.l10n_eg_edi_pos_error;
                if (error) {
                    this.dialog.add(
                        AlertDialog,
                        {
                            title: _t("ETA Error"),
                            body:
                                _t(
                                    "The receipt could not be submitted to ETA.\nResend it from Backend > Orders > Select the Order > Resend to ETA.\n\nError message:\n"
                                ) + error,
                        },
                        {}
                    );
                }
            }
        });
    },
});
