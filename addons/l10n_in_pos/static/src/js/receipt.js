odoo.define('l10n_in_pos.receipt', function (require) {
"use strict";

var models = require('point_of_sale.models');

models.load_fields('product.product', 'l10n_in_hsn_code');

var _super_orderline = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    export_for_printing: function() {
        var line = _super_orderline.export_for_printing.apply(this,arguments);
        line.l10n_in_hsn_code = this.get_product().l10n_in_hsn_code;
        return line;
    },
});

});
