import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(QRPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    async _confirm() {
        // Verify whether the payment has been recieved by QRIS

        this.setButtonsDisabled(true);

        const pm_line = this.props.line;
        let result;

        try {
            result = await this.orm.call("pos.payment.method", "l10n_id_verify_qris_status", [
                [pm_line.payment_method_id.id],
                pm_line.pos_order_id.uuid,
            ]);
        } catch {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Failure"),
                body: _t("Failure to verify QRIS payment status"),
            });
            this.setButtonsDisabled(false);
            return false;
        }

        if (!result) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Payment Status Update"),
                body: _t("Payment Status returns unpaid"),
            });
            this.setButtonsDisabled(false);
            return false;
        }
        this.setButtonsDisabled(false);
        return super._confirm();
    },
});
