import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreenPaymentLines.prototype, {
    getPaymentActionState(line) {
        if (line.payment_method_id.usesSquareApp() && line.getPaymentStatus() === "waitingCard") {
            // The payment is taken in the Square app, so send and cancel have nothing to talk to.
            return {
                id: "square_continue_app",
                title: _t("Continue on the Square app"),
                icon: "smartphone",
                actions: [
                    {
                        id: "square_cancel",
                        label: _t("Cancel"),
                        title: _t("Cancel Square Payment"),
                        action: () => this.props.deleteLine(line.uuid),
                        severity: "danger",
                    },
                ],
            };
        }

        return super.getPaymentActionState(...arguments);
    },
});
