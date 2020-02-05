odoo.define('point_of_sale.ProductDisplay', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class ProductDisplay extends PosComponent {
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
            return `${window.location.origin}/web/image?model=product.product&field=image_128&id=${this.props.product.id}`;
        }
        get pricelist() {
            const current_order = this.props.pos.get_order();
            if (current_order) {
                return current_order.pricelist;
            }
            return this.props.pos.default_pricelist;
        }
        get price() {
            const formattedUnitPrice = this.props.pos.format_currency(
                this.props.product.get_price(this.pricelist, 1),
                'Product Price'
            );
            if (this.props.product.to_weight) {
                return `${formattedUnitPrice}/${
                    this.props.pos.units_by_id[this.props.product.uom_id[0]].name
                }`;
            } else {
                return formattedUnitPrice;
            }
        }
    }

    return { ProductDisplay };
});