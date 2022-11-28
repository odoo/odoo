odoo.define('point_of_sale.ProductItem', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { ConnectionLostError, ConnectionAbortedError } = require('@web/core/network/rpc_service')
    const { identifyError } = require('point_of_sale.utils');

    class ProductItem extends PosComponent {
        /**
         * For accessibility, pressing <space> should be like clicking the product.
         * <enter> is not considered because it conflicts with the barcode.
         *
         * @param {KeyPressEvent} event
         */
        spaceClickProduct(event) {
            if (event.which === 32) {
                this.trigger('click-product', this.props.product);
            }
        }
        get imageUrl() {
            const product = this.props.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
        }
        get pricelist() {
            const current_order = this.env.pos.get_order();
            if (current_order) {
                return current_order.pricelist;
            }
            return this.env.pos.default_pricelist;
        }
        get price() {
            const formattedUnitPrice = this.env.pos.format_currency(
                this.props.product.get_display_price(this.pricelist, 1),
                'Product Price'
            );
            if (this.props.product.to_weight) {
                return `${formattedUnitPrice}/${
                    this.env.pos.units_by_id[this.props.product.uom_id[0]].name
                }`;
            } else {
                return formattedUnitPrice;
            }
        }
        async onProductInfoClick() {
            try {
                const info = await this.env.pos.getProductInfo(this.props.product, 1);
                this.showPopup('ProductInfoPopup', { info: info , product: this.props.product });
            } catch (e) {
                if (identifyError(e) instanceof ConnectionLostError||ConnectionAbortedError) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('OfflineErrorPopup'),
                        body: this.env._t('Cannot access product information screen if offline.'),
                    });
                } else {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Unknown error'),
                        body: this.env._t('An unknown error prevents us from loading product information.'),
                    });
                }
            }
        }
    }
    ProductItem.template = 'ProductItem';

    Registries.Component.add(ProductItem);

    return ProductItem;
});
