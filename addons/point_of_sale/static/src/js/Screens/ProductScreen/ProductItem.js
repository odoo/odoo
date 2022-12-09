/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class ProductItem extends PosComponent {
    /**
     * For accessibility, pressing <space> should be like clicking the product.
     * <enter> is not considered because it conflicts with the barcode.
     *
     * @param {KeyPressEvent} event
     */
    spaceClickProduct(event) {
        if (event.which === 32) {
            this.trigger("click-product", this.props.product);
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
            "Product Price"
        );
        if (this.props.product.to_weight) {
            return `${formattedUnitPrice}/${
                this.env.pos.units_by_id[this.props.product.uom_id[0]].name
            }`;
        } else {
            return formattedUnitPrice;
        }
    }
}
ProductItem.template = "ProductItem";

Registries.Component.add(ProductItem);

export default ProductItem;
