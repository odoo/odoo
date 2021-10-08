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
        }
        async willStart() {
            const order = this.env.pos.get_order();
            try {
                // check back-end method `get_product_info_pos` to see what it returns
                // We do this so it's easier to override the value returned and use it in the component template later
                this.productInfo = await this.rpc({
                    model: 'product.product',
                    method: 'get_product_info_pos',
                    args: [[this.props.product.id],
                        this.props.product.get_price(order.pricelist, this.props.quantity),
                        this.props.quantity,
                        this.env.pos.config_id],
                    kwargs: {context: this.env.session.user_context},
                });

                const priceWithoutTax = this.productInfo['all_prices']['price_without_tax'];
                const margin = priceWithoutTax - this.props.product.standard_price;
                const orderPriceWithoutTax = order.get_total_without_tax();
                const orderCost = order.get_total_cost();
                const orderMargin = orderPriceWithoutTax - orderCost;

                this.costCurrency = this.env.pos.format_currency(this.props.product.standard_price);
                this.marginCurrency = this.env.pos.format_currency(margin);
                this.marginPercent = priceWithoutTax ? Math.round(margin/priceWithoutTax * 10000) / 100 : 0;
                this.orderPriceWithoutTaxCurrency = this.env.pos.format_currency(orderPriceWithoutTax);
                this.orderCostCurrency = this.env.pos.format_currency(orderCost);
                this.orderMarginCurrency = this.env.pos.format_currency(orderMargin);
                this.orderMarginPercent = orderPriceWithoutTax ? Math.round(orderMargin/orderPriceWithoutTax * 10000) / 100 : 0;
            } catch (error) {
                this.error = error;
            }
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
