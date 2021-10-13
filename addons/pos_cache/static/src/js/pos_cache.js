odoo.define('pos_cache.pos_cache', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var { Gui } = require('point_of_sale.Gui');
var _t = core._t;

function roundUpDiv(y, x) {
    const remainder = y % x;
    return (y - remainder) / x + (remainder > 0 ? 1 : 0);
}

var posmodel_super = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    /**
     * This method will make sense if you are aware that the behavior of
     * `_meta_product_product` method in the backend is modified by pos_cache module.
     * Basically, before `after_load_server_data`, initial number of products is loaded
     * (100000 products to be exact). This method is extended, to basically perform
     * background tasks to load the remaining products from the backend.
     */
    async after_load_server_data() {
        await posmodel_super.after_load_server_data.call(this, ...arguments);
        this._loadProductInBackground();
    },
    async _loadProductInBackground() {
        const nInitiallyLoaded = Object.keys(this.db.product_by_id).length;
        const totalProductsCount = await this._getTotalProductsCount();
        const nRemaining = totalProductsCount - nInitiallyLoaded;
        if (!(nRemaining > 0)) return;
        const multiple = 100000;
        const nLoops = roundUpDiv(nRemaining, multiple);
        for (let i = 0; i < nLoops; i++) {
            await this._loadCachedProducts(i * multiple + nInitiallyLoaded, (i + 1) * multiple + nInitiallyLoaded);
        }
        Gui.showNotification(_t('All products are loaded.'), 5000);
    },
    async _getTotalProductsCount() {
        const productMeta = this.loadingInfos['product.product'];
        const domain = productMeta['domain']
        const fields = productMeta['fields']
        return this.rpc({
            model: 'pos.session',
            method: 'get_total_products_count',
            args: [[odoo.pos_session_id], domain, fields],
            context: this.session.user_context,
        });
    },
    async _loadCachedProducts(start, end) {
        const productMeta = this.loadingInfos['product.product'];
        const domain = productMeta['domain']
        const fields = productMeta['fields']
        const products = await this.rpc({
            model: 'pos.session',
            method: 'get_cached_products',
            args: [[odoo.pos_session_id], domain, fields, start, end],
            context: this.session.user_context,
        });
        const productModel = _.find(this.models, function(model){return model.model === 'product.product';});
        productModel.loaded(this, products);
    },
});

});
