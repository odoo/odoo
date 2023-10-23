/** @odoo-module **/

import { formatCurrency } from "@web/core/currency";
import { Product } from "@product/js/product_configurator/product/product"

export class SaleProduct extends Product {
    static template = 'sale_product_configurator.product';
    static props = {
        ...Product.props,
        price: { type: Number, optional: true},
        optional: Boolean,
        parent_exclusions: Object,
        parent_product_tmpl_ids: { type: Array, element: Number, optional: true },
    };
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the price, in the format of the given currency.
     *
     * @return {String} - The price, in the format of the given currency.
     */
    getFormattedPrice() {
        return formatCurrency(this.props.price, this.env.currencyId);
    }
}
