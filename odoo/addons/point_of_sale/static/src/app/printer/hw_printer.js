/* @odoo-module */

import { BasePrinter } from "@point_of_sale/app/printer/base_printer";

/**
 * Printer that sends print requests thru /hw_proxy endpoints.
 * Doesn't require pos_iot to be installed.
 */
export class HWPrinter extends BasePrinter {
    /**
     * @param {Object} params
     * @param {Function} params.rpc the web's rpc service.
     * @param {string} params.url full address of the iot box. E.g. `http://10.23.45.67:8069`.
     */
    setup(params) {
        super.setup(...arguments);
        const { rpc, url } = params;
        this.rpc = rpc;
        this.url = url;
    }

    sendAction(data) {
        return this.rpc(`${this.url}/hw_proxy/default_printer_action`, { data });
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
