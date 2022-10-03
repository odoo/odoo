odoo.define('pos_cache.pos_cache', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');


const PosCachePosGlobalState = (PosGlobalState) => class PosCachePosGlobalState extends PosGlobalState {
    async _getTotalProductsCount() {
        return this.orm.call('pos.session', 'get_total_products_count', [[odoo.pos_session_id]]);
    }
    async _loadCachedProducts(start, end) {
        const args = [[odoo.pos_session_id], start, end];
        const products = await this.orm.silent.call('pos.session', 'get_cached_products', args);
        this._loadProductProduct(products);
    }
}
Registries.Model.extend(PosGlobalState, PosCachePosGlobalState);

});
