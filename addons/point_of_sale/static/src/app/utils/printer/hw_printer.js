import { IoTDevice } from "@iot_base/device_controller";
import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";

/**
 * Printer that sends print requests through longpolling to default printer.
 * Doesn't require pos_iot to be installed.
 */
export class HWPrinter extends BasePrinter {
    /**
     * @param {Object} params
     * @param {IoTDevice} params.printer - IoTDevice class to communicate with the printer
     */
    setup(params) {
        super.setup(...arguments);
        this.printer = params.printer;
    }

    /**
     * @override
     */
    openCashbox() {
        return this.printer.action({ action: "cashbox" });
    }

    /**
     * @override
     */
    sendPrintingJob(img) {
        return this.printer.action({ action: "print_receipt", receipt: img });
    }
}
