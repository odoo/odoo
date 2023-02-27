/** @odoo-module */
import { Payment } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

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
