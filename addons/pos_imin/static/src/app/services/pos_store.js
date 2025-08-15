import { PosStore } from "@point_of_sale/app/services/pos_store";
import { EpsonPrinter } from "@point_of_sale/app/utils/printer/epson_printer";
import { IminPrinterAdapter } from "@pos_imin/app/utils/imin_printer";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    afterProcessServerData() {
        const self = this;
        return super.afterProcessServerData(...arguments).then(async function () {
            if (self.config.other_devices) {
                const iminPrinterAdapter = new IminPrinterAdapter();
                if (await iminPrinterAdapter.isAvailable) {
                    self.iminPrinterAdapter = iminPrinterAdapter; // Store the adapter for later use
                    const printerStatus = await iminPrinterAdapter.printerStatus;
                    if (printerStatus.value === 0) {
                        self.hardwareProxy.printer = self.iminPrinterAdapter;
                    }
                }
            }
        });
    },
    async printReceipt({
        basic = false,
        order = this.getOrder(),
        printBillActionTriggered = false,
    } = {}) {
        if (this.config.other_devices && this.iminPrinterAdapter) {
            const printerStatus = await this.iminPrinterAdapter.printerStatus;
            if (printerStatus.value === 0) {
                this.hardwareProxy.printer = this.iminPrinterAdapter;
            } else if (this.config.epson_printer_ip) {
                this.hardwareProxy.printer = new EpsonPrinter({ ip: this.config.epson_printer_ip });
            }
        }
        return super.printReceipt(...arguments);
    },
});
