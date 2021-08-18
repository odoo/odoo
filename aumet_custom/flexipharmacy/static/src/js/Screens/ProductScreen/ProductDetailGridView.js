    odoo.define('flexipharmacy.ProductDetailGridView', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ProductDetailGridView extends PosComponent {
        spaceClickProduct(event) {
            if (event.which === 32) {
                this.trigger('click-product', this.props.product_by_id);
            }
        }
        get imageUrl() {
            const product = this.props.product_by_id;
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
            const formattedUnitPrice = this.env.pos.format_currency(
                this.props.product_by_id.get_price(this.pricelist, 1),
                'Product Price'
            );
            if (this.props.product_by_id.to_weight) {
                return `${formattedUnitPrice}/${
                    this.env.pos.units_by_id[this.props.product_by_id.uom_id[0]].name
                }`;
            } else {
                return formattedUnitPrice;
            }
        }
    }
    ProductDetailGridView.template = 'ProductDetailGridView';

    Registries.Component.add(ProductDetailGridView);

    return ProductDetailGridView;
});
