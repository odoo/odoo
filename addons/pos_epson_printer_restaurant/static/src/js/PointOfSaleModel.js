odoo.define('pos_epson_printer_restaurant.PointOfSaleModel', function (require) {
"use strict";

const PointOfSaleModel = require('pos_restaurant.PointOfSaleModel');
const EpsonPrinter = require('pos_epson_printer.Printer');
const { patch } = require('web.utils');

patch(PointOfSaleModel.prototype, 'pos_epson_printer_restaurant', {
    _createPrinter: function (config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter(config.epson_printer_ip);
        } else {
            return this._super(...arguments);
        }
    },
});

return PointOfSaleModel;
});
