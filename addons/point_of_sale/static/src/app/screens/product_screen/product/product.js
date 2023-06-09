/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class ProductItem extends Component {
    static template = "point_of_sale.ProductItem";

    setup() {
        this.pos = usePos();
    }
    /**
     * For accessibility, pressing <space> should be like clicking the product.
     * <enter> is not considered because it conflicts with the barcode.
     *
     * @param {KeyPressEvent} event
     */
    spaceClickProduct(event) {
        if (event.which === 32) {
            this.pos.addProductToCurrentOrder(this.props.product);
        }
    }
    get imageUrl() {
        const product = this.props.product;
        return `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
    }
    get pricelist() {
        const current_order = this.pos.get_order();
        if (current_order) {
            return current_order.pricelist;
        }
        return this.pos.default_pricelist;
    }
    get price() {
        const formattedUnitPrice = this.env.utils.formatCurrency(
            this.props.product.get_display_price(this.pricelist, 1)
        );
        if (this.props.product.to_weight) {
            return `${formattedUnitPrice}/${
                this.pos.units_by_id[this.props.product.uom_id[0]].name
            }`;
        } else {
            return formattedUnitPrice;
        }
    }
}
