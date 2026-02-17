import { _t } from "@web/core/l10n/translation";
import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
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
        });
    },
});
