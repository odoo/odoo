import { Plugin, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { PosDataPlugin } from "@point_of_sale/app/plugins/pos_data_plugin";
import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";

export class PosPaymentMethodPlugin extends Plugin {
    // After PosDataPlugin (20)
    static sequence = 30;

    data = usePlugin(PosDataPlugin);
    accessRight = usePlugin(PosAccessRightPlugin);

    get config() {
        return this.data.models["pos.config"].get(odoo.pos_config_id);
    }

    /**
     * Create the payment interface of each payment method, once the data is loaded.
     * @param {import("@point_of_sale/app/services/pos_store").PosStore} pos
     */
    init(pos) {
        for (const pm of this.config.payment_method_ids) {
            const PaymentInterface = registry
                .category("pos_payment_providers")
                .get(pm.paymentInterfaceKey, null);
            pm.payment_interface = PaymentInterface ? new PaymentInterface(pos, pm) : null;
        }
    }

    /**
     * Payment methods the order may use. Patch this to add or remove methods.
     */
    getPaymentMethods(order) {
        return this.config.paymentMethods;
    }

    /**
     * Payment methods the order can use right now.
     */
    getAvailablePaymentMethods(order) {
        return this.getPaymentMethods(order).filter(
            (pm) =>
                pm.isAvailable(order) &&
                (pm.type !== "pay_later" || this.accessRight.canAccessPaymentMethod)
        );
    }

    /**
     * Payment method used when no payment line is chosen yet, may be undefined.
     */
    getFirstAvailable(order) {
        return this.getAvailablePaymentMethods(order)[0];
    }

    hasPaymentMethodType(order, type) {
        return this.getPaymentMethods(order).some((pm) => pm.type === type);
    }

    /**
     * Payment method used to validate the order without choosing one, may be undefined.
     * Applies when:
     * 1. There are no payment lines yet.
     * 2. The customer's due has been settled: the negative pay_later line is in
     *    `payment_ids` but not shown in the UI.
     */
    getFastPaymentMethod(order) {
        const paymentLines = order.payment_ids;
        if (
            !paymentLines.length ||
            (!order.is_refund &&
                paymentLines.length === 1 &&
                paymentLines[0].payment_method_id.type === "pay_later" &&
                order.currency.isNegative(paymentLines[0].amount))
        ) {
            return this.getFirstAvailable(order);
        }
    }
}

services.add(PosPaymentMethodPlugin);
