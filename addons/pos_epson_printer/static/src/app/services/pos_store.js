import { PosStore } from "@point_of_sale/app/services/pos_store";
import { EpsonPrinter } from "@pos_epson_printer/app/utils/payment/epson_printer";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        if (this.config.other_devices && this.config.epson_printer_ip) {
            this.ePosPrinter = new EpsonPrinter({ ip: this.config.epson_printer_ip });
            this.printer.setPrinter(this.ePosPrinter); // allows `this.printer.print()` as it sets the printer in "printer" service
        }
    },
    createPrinter(config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter({ ip: config.epson_printer_ip });
        } else {
            return super.createPrinter(...arguments);
        }
    },
    cashMove() {
        this.ePosPrinter?.openCashbox();
        return super.cashMove(...arguments);
    },
});
