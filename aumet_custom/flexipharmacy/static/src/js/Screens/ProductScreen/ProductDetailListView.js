    odoo.define('flexipharmacy.ProductDetailListView', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ProductDetailListView extends PosComponent {
        get highlight() {
            return this.props.ProductId !== this.props.selectedview ? '' : 'highlight';
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
    ProductDetailListView.template = 'ProductDetailListView';

    Registries.Component.add(ProductDetailListView);

    return ProductDetailListView;
});
