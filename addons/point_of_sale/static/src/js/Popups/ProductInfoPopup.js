odoo.define('point_of_sale.ProductInfoPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils')
    const { ConnectionLostError } = require('@web/core/network/rpc_service')

    /**
     * This popup needs to be self-dependent because it needs to be called from different place. In order to avoid code
     * Props:
     *  {
     *      product: a product object
     *      quantity: number
     *  }
     */
    class ProductInfoPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            Object.assign(this, this.props.info);
        }
        /**
         * @deprecated Don't remove. There might be overrides.
         */
        async willStart() {

        }
        /*
         * Since this popup need to be self dependent, in case of an error, the popup need to be closed on its own.
         */
        mounted() {
            if (this.error) {
                this.cancel();
                if (this.error.message instanceof ConnectionLostError) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Cannot access product information screen if offline.'),
                    });
                } else {
                    throw this.error;
                }
            }
        }
        searchProduct(productName) {
            posbus.trigger('search-product-from-info-popup', productName);
            this.cancel()
        }
    }

    ProductInfoPopup.template = 'ProductInfoPopup';
    Registries.Component.add(ProductInfoPopup);
});
