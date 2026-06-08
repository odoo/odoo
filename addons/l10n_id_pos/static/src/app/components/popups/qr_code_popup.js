import { props, types } from "@odoo/owl";
import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(QRPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10nIdPosProps = props({
            "paymentMethod?": types.object(),
            "order?": types.object(),
        });
        this.orm = useService("orm");
    },

    async confirm() {
        if (!this.l10nIdPosProps.paymentMethod?.id || !this.l10nIdPosProps.order?.uuid) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Verification Error"),
                body: _t("We couldn't verify the QRIS payment. Please try again."),
            });
            this.setButtonsDisabled(false);
            return false;
        }

        // Verify whether the payment has been received by QRIS
        this.setButtonsDisabled(true);

        let result;
        try {
            result = await this.orm.call("pos.payment.method", "l10n_id_verify_qris_status", [
                [this.l10nIdPosProps.paymentMethod.id],
                this.l10nIdPosProps.order.uuid,
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
        return super.confirm();
    },

    setButtonsDisabled(disabled) {
        for (const button of [...document.querySelectorAll(".modal-content button")]) {
            button.disabled = disabled;
        }
    },
});
