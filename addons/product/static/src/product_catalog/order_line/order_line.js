import { onWillRender } from "@web/owl2/utils";
import { Component, onMounted, Portal, signal } from "@odoo/owl";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogOrderLine extends Component {
    static template = "product.ProductCatalogOrderLine";
    static props = {
        isSample: { type: Boolean, optional: true },
        productId: Number,
        quantity: Number,
        price: Number,
        productType: String,
        uomId: { type: Number, optional: true },
        uomDisplayName: { type: String, optional: true },
        availableUoms: { type: Array, optional: true },
        productUomFactor: { type: Number, optional: true },
        productUomDisplayName: { type: String, optional: true },
        sellerUomFactor: { type: Number, optional: true },
        code: { type: String, optional: true },
        readOnly: { type: Boolean, optional: true },
        warning: { type: String, optional: true },
    };
    static components = { Portal };

    portalTarget = signal(null);
    rev = 0;

    setup() {
        this.hasMultipleUoms = this.props.availableUoms && this.props.availableUoms.length > 1;
        onMounted(() => {
            this.portalTarget.set(document.querySelector(`#product-${this.props.productId}-price`));
        });
        onWillRender(() => {
            this.rev++;
        });
    }

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
        const { currencyId, digits } = this.env;
        return formatMonetary(this.props.price, { currencyId, digits });
    }

    get productUnitPrice() {
        const { currencyId, digits } = this.env;
        const productUnitPrice = this.props.price * (this.props.productUomFactor || 1);
        return formatMonetary(productUnitPrice, { currencyId, digits });
    }

    get quantity() {
        const digits = [false, this.env.precision];
        const options = { digits, decimalPoint: ".", thousandsSep: "" };
        return parseFloat(formatFloat(this.props.quantity, options));
    }

    get uomSelectStyle() {
        const name = this.props.uomDisplayName || "";
        return `width: ${name.length + 5}ch;`;
    }

    onUomChange(ev) {
        this.env.setUom(parseInt(ev.target.value));
    }

    get showPrice() {
        return true;
    }

    get displayPriceByProductUoM() {
        const { uomDisplayName, productUomDisplayName } = this.props;
        return (
            uomDisplayName != productUomDisplayName &&
            this.productUnitPrice &&
            productUomDisplayName &&
            this.showPrice
        );
    }
}
