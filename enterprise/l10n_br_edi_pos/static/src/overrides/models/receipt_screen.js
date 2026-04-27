import { _t } from "@web/core/l10n/translation";
import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            const error = this.pos.get_order().l10n_br_avatax_error;
            if (error) {
                this.dialog.add(
                    AlertDialog,
                    {
                        title: _t("NFCe error"),
                        body:
                            _t(
                                `We could not send the NFCe for this order.\n\nTo send it, go to Orders or Backend > Paid Order or Orders > Select the Order > Details > Send NFCe.\n\n`
                            ) + error,
                    },
                    {}
                );
            }
        });
    },
});
