import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    setPartnerToCurrentOrder(partner) {
        if (this.config.l10n_eg_edi_pos_enable && partner?.is_company) {
            this.dialog.add(AlertDialog, {
                title: _t("ETA Validation Error"),
                body: _t("You're not allowed to issue sales receipts to business buyers."),
            });
            return;
        }
        return super.setPartnerToCurrentOrder(...arguments);
    },
});
