odoo.define('pos_adyen.models', function (require) {
const { register_payment_method, Payment } = require('point_of_sale.models');
const PaymentAdyen = require('pos_adyen.payment');
const Registries = require('point_of_sale.Registries');

register_payment_method('adyen', PaymentAdyen);

const PosAdyenPayment = (Payment) => class PosAdyenPayment extends Payment {
    constructor(obj, options) {
        super(...arguments);
        this.terminalServiceId = this.terminalServiceId || null;
    }
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.terminal_service_id = this.terminalServiceId;
        return json;
    }
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.terminalServiceId = json.terminal_service_id;
    }
    setTerminalServiceId(id) {
        this.terminalServiceId = id;
    }
}
Registries.Model.extend(Payment, PosAdyenPayment);
});
