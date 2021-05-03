odoo.define('pos_epson_printer.PointOfSaleModel', function (require) {
    'use strict';

    const { patch } = require('web.utils');
    const EpsonPrinter = require('pos_epson_printer.Printer');
    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');

    patch(PointOfSaleModel.prototype, 'pos_epson_printer', {
        async _fetchAndProcessPosData() {
            await this._super(...arguments);
            if (this.config.other_devices && this.config.epson_printer_ip) {
                this.proxy.printer = new EpsonPrinter(this.config.epson_printer_ip, this);
            }
        },
    });

    return PointOfSaleModel;
});
