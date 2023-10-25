/** @odoo-module */
import { Component } from "@odoo/owl";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogOrderLine extends Component {
    static template = "ProductCatalogOrderLine";
    static props = {
        productId: Number,
        quantity: Number,
        price: Number,
        readOnly: { type: Boolean, optional: true },
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    isInOrder() {
        return this.props.quantity !== 0;
    }

    get disableRemove() {
        return false;
    }

    get disabledButtonTooltip() {
        return "";
    }

    get price() {
        const { currencyId, digits } = this.env;
        return formatMonetary(this.props.price, { currencyId, digits });
    }

    get quantity() {
        const digits = [false, this.env.precision];
        const options = { digits, decimalPoint: ".", thousandsSep: "" };
        return parseFloat(formatFloat(this.props.quantity, options));
    }
}
