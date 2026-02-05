import { useLayoutEffect } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { FeedbackScreen } from "@point_of_sale/app/screens/feedback_screen/feedback_screen";

patch(FeedbackScreen.prototype, {
    setup() {
        super.setup();
        useLayoutEffect(
            () => {
                if (this.state.loading === false) {
                    const error = this.currentOrder.l10n_jo_edi_pos_error;
                    if (error) {
                        this.dialog.add(
                            AlertDialog,
                            {
                                title: _t("JoFotara Error"),
                                body:
                                    _t(
                                        `The receipt is stuck due to an Error.\nTo send it, go to Orders > Select the Order > Details > JoFotara or Backend > Orders > Select the Order > JoFotara.\n\nError message:\n`
                                    ) + error,
                            },
                            {}
                        );
                    }
                }
            },
            () => [this.state.loading]
        );
    },
});
