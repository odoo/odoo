odoo.define('l10n_co_pos.pos', function (require) {
"use strict";

var { PosGlobalState, Order } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');

const L10nCoPosGlobalState = (PosGlobalState) => class L10nCoPosGlobalState extends PosGlobalState {
    is_colombian_country() {
        return this.company.country.code === 'CO';
    }
}
Registries.Model.extend(PosGlobalState, L10nCoPosGlobalState);

const L10nCoPosOrder = (Order) => class L10nCoPosOrder extends Order {
    export_for_printing() {
        var result = super.export_for_printing(...arguments);
        result.l10n_co_dian = this.get_l10n_co_dian();
        return result;
    }
    set_l10n_co_dian(l10n_co_dian) {
        this.l10n_co_dian = l10n_co_dian;
    }
    get_l10n_co_dian() {
        return this.l10n_co_dian;
    }
    wait_for_push_order() {
        var result = super.wait_for_push_order(...arguments);
        result = Boolean(result || this.pos.is_colombian_country());
        return result;
    }
}
Registries.Model.extend(Order, L10nCoPosOrder);

});
