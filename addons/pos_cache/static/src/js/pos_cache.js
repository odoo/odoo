odoo.define('pos_cache.pos_cache', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');


const PosCachePosGlobalState = (PosGlobalState) => class PosCachePosGlobalState extends PosGlobalState {
    async _getTotalProductsCount() {
        return this.env.services.rpc({
            model: 'pos.session',
            method: 'get_total_products_count',
            args: [[odoo.pos_session_id]],
            context: this.env.session.user_context,
        });
    }
    async _loadCachedProducts(start, end) {
        const products = await this.env.services.rpc({
            model: 'pos.session',
            method: 'get_cached_products',
            args: [[odoo.pos_session_id], start, end],
            context: this.env.session.user_context,
        });
        this._loadProductProduct(products);
    }
}
Registries.Model.extend(PosGlobalState, PosCachePosGlobalState);

});
