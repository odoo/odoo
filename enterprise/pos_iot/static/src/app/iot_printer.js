import { BasePrinter } from "@point_of_sale/app/printer/base_printer";

/**
 * Used to send print requests to the IoT box thru the provided `device` - a `DeviceController` instance.
 */
export class IoTPrinter extends BasePrinter {
    setup({ device }) {
        super.setup(...arguments);
        this.device = device;
    }

    /**
     * @override
     */
    openCashbox() {
        return this.device.action({ action: "cashbox" });
    }

    /**
     * @override
     */
    sendPrintingJob(img) {
        return this.device.action({ action: "print_receipt", receipt: img });
    }
}
