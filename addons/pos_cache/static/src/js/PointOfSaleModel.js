odoo.define('pos_cache.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const session = require('web.session');
    const { Mutex } = require('web.concurrency');
    const { patch } = require('web.utils');
    const { _t } = require('web.core');

    const backgroundMutex = new Mutex();

    function roundUpDiv(y, x) {
        const remainder = y % x;
        return (y - remainder) / x + (remainder > 0 ? 1 : 0);
    }

    patch(PointOfSaleModel.prototype, 'pos_cache', {
        /**
         * This method will make sense if you are aware that the behavior of
         * `_load_product_product` method in the backend is modified by pos_cache module.
         * Basically, at `_fetchAndProcessPosData`, initial number of products is loaded
         * (100000 products to be exact). This method is called after the UI is ready, which
         * basically performs background tasks to load the remaining products from the backend.
         */
        async _afterDoneLoading() {
            await this._super(...arguments);
            const nInitiallyLoaded = this.getRecords('product.product').length;
            const totalProductsCount = await this._getTotalProductsCount();
            const nRemaining = totalProductsCount - nInitiallyLoaded;
            if (!(nRemaining > 0)) return;
            const multiple = 100000;
            const nLoops = roundUpDiv(nRemaining, multiple);
            // use different mutex when calling the action so that the ui can be used while loading the remaining products.
            for (let i = 0; i < nLoops; i++) {
                await this.actionHandler(
                    {
                        name: 'actionLoadProducts',
                        args: [i * multiple + nInitiallyLoaded, (i + 1) * multiple + nInitiallyLoaded],
                    },
                    backgroundMutex
                );
            }
            this.ui.showNotification(
                _t('All products are loaded. The images are being loaded in the background.'),
                5000
            );
        },
        async _getTotalProductsCount() {
            return await this._rpc({
                model: 'pos.session',
                method: 'get_total_products_count',
                args: [[odoo.pos_session_id]],
                context: session.user_context,
            });
        },
        async actionLoadProducts(start, end) {
            const products = await this._rpc({
                model: 'pos.session',
                method: 'get_cached_products',
                args: [[odoo.pos_session_id], start, end],
                context: session.user_context,
            });
            const productsContainer = this.data.records['product.product'];
            for (const product of products) {
                productsContainer[product.id] = product;
            }
            this._addProducts(products);
            // No need to await on loading the images. We just queue each image loading as micro tasks.
            this.loadImages(products.map((product) => this.getImageUrl('product.product', product)));
        },
    });

    return PointOfSaleModel;
});
