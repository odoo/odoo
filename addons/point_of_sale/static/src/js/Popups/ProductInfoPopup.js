odoo.define('point_of_sale.ProductInfoPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { identifyError } = require('point_of_sale.utils');
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
        setup() {
            super.setup();
            owl.onWillStart(this.onWillStart);
        }
        async onWillStart() {
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
                        this.env.pos.config.id],
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
                this.cancel();
                if (identifyError(error) instanceof ConnectionLostError) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Cannot access product information screen if offline.'),
                    });
                } else {
                    throw error;
                }
            }
        }
        searchProduct(productName) {
            this.env.posbus.trigger('search-product-from-info-popup', productName);
            this.cancel()
        }
        _hasMarginsCostsAccessRights() {
            const isAccessibleToEveryUser = this.env.pos.config.is_margins_costs_accessible_to_every_user;
            const isCashierManager = this.env.pos.get_cashier().role === 'manager';
            return isAccessibleToEveryUser || isCashierManager;
        }
    }

    ProductInfoPopup.template = 'ProductInfoPopup';
    ProductInfoPopup.defaultProps= { confirmKey: false };
    Registries.Component.add(ProductInfoPopup);
});
