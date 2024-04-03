odoo.define('pos_cache.chrome', function (require) {
    'use strict';

const Chrome = require('point_of_sale.Chrome');
const Registries = require('point_of_sale.Registries');

function roundUpDiv(y, x) {
    const remainder = y % x;
    return (y - remainder) / x + (remainder > 0 ? 1 : 0);
}

const PosCacheChrome = (Chrome) => class PosCacheChrome extends Chrome {
    _runBackgroundTasks() {
        super._runBackgroundTasks();
        if (!this.env.pos.config.limited_products_loading) {
            this._loadRemainingProducts();
        }
    }
    async _loadRemainingProducts() {
        const nInitiallyLoaded = Object.keys(this.env.pos.db.product_by_id).length;
        const totalProductsCount = await this.env.pos._getTotalProductsCount();
        const nRemaining = totalProductsCount - nInitiallyLoaded;
        if (!(nRemaining > 0)) return;
        const multiple = 100000;
        const nLoops = roundUpDiv(nRemaining, multiple);
        for (let i = 0; i < nLoops; i++) {
            await this.env.pos._loadCachedProducts(i * multiple + nInitiallyLoaded, (i + 1) * multiple + nInitiallyLoaded);
        }
        this.showNotification(this.env._t('All products are loaded.'), 5000);
    }
};
Registries.Component.extend(Chrome, PosCacheChrome);
});
