odoo.define('pos_epson_printer_restaurant.multiprint', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
var EpsonPrinter = require('pos_epson_printer.Printer');
const Registries = require('point_of_sale.Registries');

// The override of create_printer needs to happen after its declaration in
// pos_restaurant. We need to make sure that this code is executed after the
// multiprint file in pos_restaurant.
require('pos_restaurant.multiprint');


const PosEpsonResPosGlobalState = (PosGlobalState) => class PosEpsonResPosGlobalState extends PosGlobalState {
    create_printer(config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter(config.epson_printer_ip);
        } else {
            return super.create_printer(...arguments);
        }
    }
}
Registries.Model.extend(PosGlobalState, PosEpsonResPosGlobalState);
});
