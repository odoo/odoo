odoo.define('pos_epson_printer.pos_epson_printer', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
var EpsonPrinter = require('pos_epson_printer.Printer');
const Registries = require('point_of_sale.Registries');


const PosEpsonPosGlobalState = (PosGlobalState) => class PosEpsonPosGlobalState extends PosGlobalState {
    after_load_server_data() {
        var self = this;
        return super.after_load_server_data(...arguments).then(function () {
            if (self.config.other_devices && self.config.epson_printer_ip) {
                self.env.proxy.printer = new EpsonPrinter(self.config.epson_printer_ip , self);
            }
        });
    }
}
Registries.Model.extend(PosGlobalState, PosEpsonPosGlobalState);

});
