import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setTerminalServiceId(id) {
        this.terminalServiceId = id;
    },
});
