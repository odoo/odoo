/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import { EpsonPrinter } from "@pos_epson_printer/js/epson_printer";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "pos_epson_printer.PosGlobalState", {
    after_load_server_data() {
        var self = this;
        return this._super(...arguments).then(function () {
            if (self.config.other_devices && self.config.epson_printer_ip) {
                self.hardwareProxy.printer = new EpsonPrinter({ ip: self.config.epson_printer_ip });
            }
        });
    },
    create_printer(config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter({ ip: config.epson_printer_ip });
        } else {
            return this._super(...arguments);
        }
    },
});
