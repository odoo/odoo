import { Component } from "@odoo/owl";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogOrderLine extends Component {
    static template = "product.ProductCatalogOrderLine";
    static props = {
        productId: Number,
        quantity: Number,
        price: Number,
        productType: String,
        packaging: { type: Object, optional: true },
        readOnly: { type: Boolean, optional: true },
        warning: { type: String, optional: true},
    };

    /**
     * Focus input text when clicked
     * @param {Event} ev 
     */
    _onFocus(ev) {
        ev.target.select();
    }

    addPackagingQty() {
        this.env.updatePackagingQuantity(this.props.packaging);
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

    get showPrice() {
        return true;
    }
}
