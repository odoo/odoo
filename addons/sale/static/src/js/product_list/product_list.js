/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { Product } from "../product/product";

export class ProductList extends Component {
    static components = { Product };
    static template = "sale.ProductList";
    static props = {
        products: Array,
        areProductsOptional: { type: Boolean, optional: true },
    };
    static defaultProps = {
        areProductsOptional: false,
    };

    setup() {
        this.optionalProductsTitle = _t("Add optional products");
    }

    get totalMessage() {
        return _t("Total: %s", this.getFormattedTotal());
    }

    /**
     * Return the total of the product in the list, in the currency of the `sale.order`.
     *
     * @return {String} - The sum of all items in the list, in the currency of the `sale.order`.
     */
    getFormattedTotal() {
        return formatCurrency(
            this.props.products.reduce(
                (totalPrice, product) => totalPrice + product.price * product.quantity,
                0
            ),
            this.env.currency.id,
        );
    }
}
