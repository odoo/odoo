odoo.define('l10n_co_pos.pos', function (require) {
"use strict";

var models = require('point_of_sale.models');

models.PosModel = models.PosModel.extend({
    is_colombian_country: function () {
        return this.company.country.code === 'CO';
    },
});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    export_for_printing: function () {
        var result = _super_order.export_for_printing.apply(this, arguments);
        result.l10n_co_dian = this.get_l10n_co_dian();
        return result;
    },
    set_l10n_co_dian: function (l10n_co_dian) {
        this.l10n_co_dian = l10n_co_dian;
    },
    get_l10n_co_dian: function () {
        return this.l10n_co_dian;
    },
    wait_for_push_order: function () {
        var result = _super_order.wait_for_push_order.apply(this, arguments);
        result = Boolean(result || this.pos.is_colombian_country());
        return result;
    }
});

});
