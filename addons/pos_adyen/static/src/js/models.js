/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { Payment } from "@point_of_sale/app/store/models";
import { PaymentAdyen } from "@pos_adyen/js/payment_adyen";
import { patch } from "@web/core/utils/patch";

register_payment_method("adyen", PaymentAdyen);

patch(Payment.prototype, "pos_adyen.Payment", {
    setup() {
        this._super(...arguments);
        this.terminalServiceId = this.terminalServiceId || null;
    },
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        json.terminal_service_id = this.terminalServiceId;
        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        this.terminalServiceId = json.terminal_service_id;
    },
    setTerminalServiceId(id) {
        this.terminalServiceId = id;
    },
});
