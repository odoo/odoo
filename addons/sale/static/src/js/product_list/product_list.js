/** @odoo-module */

import { Component } from "@odoo/owl";
import { SaleProduct } from "@sale/js/product/product";
import { formatCurrency } from "@web/core/currency";

export class ProductList extends Component {
    static components = { SaleProduct };
    static template = "sale_product_configurator.productList";
    static props = {
        products: Array,
        areProductsOptional: { type: Boolean, optional: true },
    };
    static defaultProps = {
        areProductsOptional: false,
    };

    /**
     * Return the total of the product in the list, in the currency of the record.
     *
     * @return {String} - The sum of all items in the list, in the currency of the record.
     */
    getFormattedTotal() {
        return formatCurrency(
            this.props.products.reduce(
                (totalPrice, product) => totalPrice + product.price * product.quantity,
                0
            ),
            this.env.currencyId
        );
    }
}
