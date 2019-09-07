odoo.define('pos_epson_printer.pos_epson_printer', function (require) {
"use strict";

var models = require('point_of_sale.models');
var PaymentScreenWidget = require('point_of_sale.screens').PaymentScreenWidget;
var EpsonPrinter = require('pos_epson_printer.Printer');

var posmodel_super = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    after_load_server_data: function () {
        var self = this;
        return posmodel_super.after_load_server_data.apply(this, arguments).then(function () {
            if (self.config.other_devices && self.config.epson_printer_ip) {
                self.proxy.printer = new EpsonPrinter(self.config.epson_printer_ip , self);
            }
        });
    },
});

});
