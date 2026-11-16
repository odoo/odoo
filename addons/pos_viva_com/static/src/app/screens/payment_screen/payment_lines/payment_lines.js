import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { useVivaApp } from "@pos_viva_com/app/hooks/use_viva_app";
import { _t } from "@web/core/l10n/translation";
import { setVivaAppEnabled } from "@pos_viva_com/app/utils/viva_app";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup();
        this.vivaApp = useVivaApp();
    },

    getPaymentActionState(line) {
        if (this.vivaApp.use(line.payment_method_id)) {
            return {
                id: "viva_continue_app",
                title: _t("Continue on Viva app"),
                icon: "smartphone",
                actions: [
                    {
                        id: "viva_use_terminal",
                        label: _t("Use terminal instead"),
                        title: _t("Stop using the Viva app on this device"),
                        action: () => {
                            this.props.deleteLine(line.uuid);
                            setVivaAppEnabled(false);
                        },
                        severity: "warning",
                    },
                ],
            };
        }
        return super.getPaymentActionState(...arguments);
    },
});
