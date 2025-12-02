import { rpc } from "@web/core/network/rpc";

import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

/**
 * Printer that sends print requests thru /hw_proxy endpoints.
 * Doesn't require pos_iot to be installed.
 */
export class HWPrinter extends BasePrinter {
    /**
     * @param {Object} params
     * @param {string} params.url full address of the iot box. E.g. `http://10.23.45.67:8069`.
     */
    setup(params) {
        super.setup(...arguments);
        this.url = params.url;
    }

    sendAction(data) {
        return rpc(`${this.url}/hw_proxy/default_printer_action`, { data });
    }

    /**
     * @override
     */
    openCashbox() {
        return this.sendAction({ action: "cashbox" });
    }

    /**
     * @override
     */
    sendPrintingJob(img) {
        return this.sendAction({ action: "print_receipt", receipt: img });
    }
}
