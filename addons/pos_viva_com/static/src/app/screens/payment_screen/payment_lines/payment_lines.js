import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { useVivaApp } from "../../../hooks/use_viva_app";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup();
        this.vivaApp = useVivaApp();
    },

    getPaymentActionState(line) {
        if (this.vivaApp.isIntegrated(line)) {
            return {
                id: "viva_continue_app",
                title: _t("Continue on Viva app"),
                icon: "fa fa-mobile",
                actions: [
                    {
                        id: "viva_reset_integration",
                        label: _t("Reset Integration"),
                        title: _t("Reset Viva Integration"),
                        action: () => this.vivaApp.resetIntegration(line),
                        severity: "danger",
                    },
                ],
            };
        }

        return super.getPaymentActionState(...arguments);
    },
});
