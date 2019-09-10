odoo.define('pos_epson_printer_restaurant.multiprint', function (require) {
"use strict";

var models = require('point_of_sale.models');
var EpsonPrinter = require('pos_epson_printer.Printer');

// The override of create_printer needs to happen after its declaration in
// pos_restaurant. We need to make sure that this code is executed after the
// multiprint file in pos_restaurant.
require('pos_restaurant.multiprint');

models.load_fields("restaurant.printer", ["epson_printer_ip"]);

var _super_posmodel = models.PosModel.prototype;

models.PosModel = models.PosModel.extend({
    create_printer: function (config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter(config.epson_printer_ip , posmodel);
        } else {
            return _super_posmodel.create_printer.apply(this, arguments);
        }
    },
});
});
