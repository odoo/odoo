import { Component } from "@odoo/owl";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogOrderLine extends Component {
    static template = "product.ProductCatalogOrderLine";
    static props = {
        childField: String,
        code: { type: String, optional: true },
        currencyId: { type: Number, optional: true },
        digits: { type: Array, optional: true },
        displayUoM: Boolean,
        isSample: { type: Boolean, optional: true },
        orderId: { type: Number | Boolean, optional: true },
        orderResModel: String,
        price: Number,
        precision: { type: Number, optional: true },
        productId: Number,
        productType: String,
        quantity: Number,
        readOnly: { type: Boolean, optional: true },
        uomDisplayName: String,
        warning: { type: String, optional: true },
        addProduct: Function,
        decreaseQuantity: Function,
        increaseQuantity: Function,
        removeProduct: Function,
        setQuantity: Function,
    };

    /**
     * Focus input text when clicked
     * @param {Event} ev
     */
    _onFocus(ev) {
        ev.target.select();
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
        const params = { currencyId: this.props.currencyId, digits: this.props.digits };
        return formatMonetary(this.props.price, params);
    }

    get quantity() {
        const options = { digits: this.props.digits, decimalPoint: ".", thousandsSep: "" };
        return parseFloat(formatFloat(this.props.quantity, options));
    }

    get showPrice() {
        return true;
    }
}
