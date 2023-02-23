/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import { EpsonPrinter } from "@pos_epson_printer/js/printers";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "pos_epson_printer.PosGlobalState", {
    after_load_server_data() {
        var self = this;
        return this._super(...arguments).then(function () {
            if (self.config.other_devices && self.config.epson_printer_ip) {
                self.env.proxy.printer = new EpsonPrinter(self.config.epson_printer_ip, self);
            }
        });
    },
});
