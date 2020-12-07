odoo.define('pos_cache.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const session = require('web.session');
    const { patch } = require('web.utils');
    const { _t } = require('web.core');

    patch(PointOfSaleModel.prototype, 'pos_cache', {
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
        async actionNotifyDoneLoadingProducts() {
            this.ui.showNotification(
                _t('All products are loaded. The images are being loaded in the background.'),
                5000
            );
        },
    });

    return PointOfSaleModel;
});
