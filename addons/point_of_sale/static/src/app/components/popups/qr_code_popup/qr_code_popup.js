import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, usePlugin } from "@odoo/owl";
import { PaymentMethod } from "@pos_payment_method/payment_method";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export const qrPopupProps = {
    amount: t.string(),
    qrCode: t.string(),
    paymentInterface: t.instanceOf(PaymentMethod),
    transactionId: t.string(),
    close: t.function(),
    provider: t.or([t.string(), t.boolean()]).optional(),
};

export class QRPopup extends Component {
    static template = "point_of_sale.QRPopup";
    static components = { Dialog };

    props = useProps(qrPopupProps);

    setup() {
        this.dialog = usePlugin(DialogPlugin);
        this.state = proxy({ qrLoaded: false, loading: false });
    }

    onQrLoaded() {
        // Force the skeleton to avoid flashing effect
        setTimeout(() => {
            this.state.qrLoaded = true;
        }, 150);
    }

    async confirm() {
        this.state.loading = true;
        try {
            const result = await this.props.paymentInterface.getTransactionStatus(
                this.props.transactionId
            );
            if (result.status === "pending") {
                this.dialog.add(AlertDialog, {
                    title: _t("QR payment pending"),
                    body: _t("The QR code payment is still processing."),
                });
            }
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Failed to verify QR payment"),
                body: error?.data?.message ?? error?.message ?? error,
            });
        } finally {
            this.state.loading = false;
        }
    }
}
