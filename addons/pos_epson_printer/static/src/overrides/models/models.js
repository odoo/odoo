import { PosStore } from "@point_of_sale/app/store/pos_store";
import { EpsonPrinter } from "@pos_epson_printer/app/epson_printer";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    afterProcessServerData() {
        var self = this;
        return super.afterProcessServerData(...arguments).then(function () {
            if (self.config.other_devices && self.config.epson_printer_ip) {
                self.hardwareProxy.printer = new EpsonPrinter({ ip: self.config.epson_printer_ip });
            }
        });
    },
    create_printer(config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter({ ip: config.epson_printer_ip });
        } else {
            return super.create_printer(...arguments);
        }
    },
});
