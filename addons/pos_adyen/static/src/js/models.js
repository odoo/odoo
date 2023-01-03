/** @odoo-module */
import { register_payment_method, Payment } from "@point_of_sale/js/models";
import PaymentAdyen from "@pos_adyen/js/payment_adyen";
import Registries from "@point_of_sale/js/Registries";

register_payment_method("adyen", PaymentAdyen);

const PosAdyenPayment = (Payment) =>
    class PosAdyenPayment extends Payment {
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
    };
Registries.Model.extend(Payment, PosAdyenPayment);
