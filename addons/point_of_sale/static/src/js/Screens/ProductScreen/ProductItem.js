odoo.define('point_of_sale.ProductItem', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

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
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        }
        get pricelist() {
            const current_order = this.env.pos.get_order();
            if (current_order) {
                return current_order.pricelist;
            }
            return this.env.pos.default_pricelist;
        }
        get price() {
            const formattedUnitPrice = this.env.pos.format_currency(this.price_with_taxes, 'Product Price');
            if (this.props.product.to_weight) {
                return `${formattedUnitPrice}/${
                    this.env.pos.units_by_id[this.props.product.uom_id[0]].name
                }`;
            } else {
                return formattedUnitPrice;
            }
        }
        get price_with_taxes() {
            var taxes = [];
            this.props.product.taxes_id.forEach(id => taxes.push(this.env.pos.taxes_by_id[id]));
            var all_taxes = this.env.pos.compute_all(taxes, this.props.product.get_price(this.pricelist, 1), 1, this.env.pos.currency.rounding);
            return this.env.pos.config.iface_tax_included === "total"? all_taxes.total_included: all_taxes.total_excluded;
        }
    }
    ProductItem.template = 'ProductItem';

    Registries.Component.add(ProductItem);

    return ProductItem;
});
