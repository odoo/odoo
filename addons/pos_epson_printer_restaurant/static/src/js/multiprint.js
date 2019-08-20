odoo.define('pos_epson_printer_restaurant.multiprint', function (require) {
"use strict";

var models = require('point_of_sale.models');
var EpsonPrinter = require('pos_epson_printer.Printer');

models.load_fields("restaurant.printer", ["printer_type", "epson_printer_ip"]);

models.PosModel = models.PosModel.extend({
    create_printer: function (config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter(config.epson_printer_ip , posmodel);
        } else {
            this._super(config);
        }
    },
});
});
