/** @odoo-module */
import { Component } from "@odoo/owl";
import { formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogSOL extends Component {
    static template = "sale.ProductCatalogSOL";
    static props = {
        productId: Number,
        quantity: Number,
        price: Number,
        readOnly: { type: Boolean, optional: true },
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    isInSaleOrder() {
        return this.props.quantity !== 0;
    }

    get price() {
        return formatMonetary(this.props.price, { currencyId: this.env.currencyId });
    }

}
