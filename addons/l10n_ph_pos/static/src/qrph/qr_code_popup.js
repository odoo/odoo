import {
    QRPopup,
    qrPopupProps,
} from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { t } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

Object.assign(qrPopupProps, {
    paymentMethod: t.object().optional(),
    order: t.object().optional(),
});

patch(QRPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.verifying = false;
    },

    async confirm() {
        // Nothing proves a QRPH code was scanned, so ask Maya before letting the order through.
        if (this.verifying || !this.props.paymentMethod?.id || !this.props.order?.uuid) {
            return super.confirm();
        }

        this.verifying = true;
        try {
            const paid = await this.orm.call(
                "pos.payment.method",
                "l10n_ph_qrph_verify_payment_status",
                [[this.props.paymentMethod.id], this.props.order.uuid, this.props.order.amount]
            );
            if (!paid) {
                this.dialog.add(AlertDialog, {
                    title: _t("Payment not received"),
                    body: _t("Maya has not received this QRPH payment yet."),
                });
                return false;
            }
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Payment not verified"),
                body: error.data?.message || _t("Could not check the QRPH payment with Maya."),
            });
            return false;
        } finally {
            this.verifying = false;
        }

        return super.confirm();
    },
});
