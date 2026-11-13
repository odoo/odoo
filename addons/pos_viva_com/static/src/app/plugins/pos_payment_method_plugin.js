import { PosPaymentMethodPlugin } from "@point_of_sale/app/plugins/pos_payment_method_plugin";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import {
    isAndroidDevice,
    isVivaAppEnabled,
    setVivaAppEnabled,
} from "@pos_viva_com/app/utils/viva_app";

patch(PosPaymentMethodPlugin.prototype, {
    computeDefaultGroups() {
        const groups = super.computeDefaultGroups();
        // On Android, the Viva app can be used instead of the terminal: always
        // group the Viva methods so that the user is asked about it once.
        if (isAndroidDevice() && !groups.viva_com) {
            const vivaMethods = this.config.paymentMethods.filter(
                (pm) => pm.payment_interface && pm.payment_provider === "viva_com"
            );
            if (vivaMethods.length) {
                groups.viva_com = vivaMethods;
            }
        }
        return groups;
    },
    getProviderOptions(provider) {
        if (provider === "viva_com" && isAndroidDevice()) {
            return [
                {
                    name: "use_app",
                    label: _t("Use the Viva app installed on this device"),
                    value: isVivaAppEnabled(),
                },
            ];
        }
        return super.getProviderOptions(...arguments);
    },
    setProviderOptions(provider, options) {
        if (provider === "viva_com" && "use_app" in options) {
            setVivaAppEnabled(options.use_app);
            return;
        }
        return super.setProviderOptions(...arguments);
    },
});
