/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/js/models";
import { EpsonPrinter } from "@pos_epson_printer/js/printers";
import { patch } from "@web/core/utils/patch";

// The override of create_printer needs to happen after its declaration in
// pos_restaurant. We need to make sure that this code is executed after the
// models file in pos_restaurant.
import "@pos_restaurant/js/models";

patch(PosGlobalState.prototype, "pos_epson_printer_restaurant.PosGlobalState", {
    create_printer(config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter(config.epson_printer_ip, this);
        } else {
            return this._super(...arguments);
        }
    },
});
