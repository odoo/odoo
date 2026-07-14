import { _t } from "@web/core/l10n/translation";
import { onWillRender } from "@web/owl2/utils";
import { Component, onMounted, Portal, signal } from "@odoo/owl";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogOrderLine extends Component {
    static template = "product.ProductCatalogOrderLine";
    static props = {
        isSample: { type: Boolean, optional: true },
        productId: Number,

        // TODO make optional with default to 0
        quantity: Number,

        // price data (only shown if provided)
        price: { type: Number, optional: true },

        // uom data (if feature enabled)
        uomId: { type: Number, optional: true },
        productUomId: { type: Number, optional: true },
        availableUoms: { type: Array, optional: true },

        // other optional data
        minimumProductQuantity: { type: Number, optional: true },
        minimumLineQuantity: { type: Number, optional: true },
        readOnly: { type: Boolean, optional: true },
        warning: { type: String, optional: true },
        subtotal: { type: Number, optional: true },
    };
    static components = { Portal };

    portalTarget = signal(null);
    rev = 0;

    setup() {
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
        if (this.props.quantity === this.props.minimumLineQuantity) {
            return true;
        }
        return false;
    }

    get decreaseButtonTooltip() {
        if (this.props.quantity === this.props.minimumLineQuantity) {
            return _t(
                "You cannot decrease the quantity below %(minimum_quantity)s.",
                { minimum_quantity : this.props.minimumLineQuantity }
            );
        }
        return "";
    }

    get price() {
        const { currencyId, digits } = this.env;
        return formatMonetary(this.props.price, { currencyId, digits });
    }

    get productUnitPrice() {
        const { currencyId, digits } = this.env;
        const productUnitPrice = this.props.price * (this.productUomFactor || 1);
        return formatMonetary(productUnitPrice, { currencyId, digits });
    }

    get quantity() {
        const digits = [false, this.env.precision];
        const options = { digits, decimalPoint: ".", thousandsSep: "" };
        return parseFloat(formatFloat(this.props.quantity, options));
    }

    get isUoMFeatureEnabled() {
        return this.props.availableUoms?.length > 0;
    }

    get hasMultipleUoms() {
        return this.props.availableUoms && this.props.availableUoms.length > 1;
    }

    get uom() {
        return this.props.availableUoms?.find((elem) => elem.id == this.props.uomId);
    }

    get uomDisplayName() {
        return this.uom?.display_name;
    }

    get productUom() {
        return this.props.availableUoms?.find((elem) => elem.id == this.props.productUomId)
    }

    get productUomDisplayName() {
        return this.productUom?.display_name;
    }

    get productUomFactor() {
        return this.productUom.factor / this.uom.factor;
    }

    get uomSelectStyle() {
        const name = this.props.uomDisplayName || "";
        return `width: ${name.length + 5}ch;`;
    }

    onUomChange(ev) {
        this.env.setUom(parseInt(ev.target.value));
    }

    get showPrice() {
        return this.props.price !== undefined;
    }

    get displayPriceByProductUoM() {
        return (
            this.showPrice
            && this.isUoMFeatureEnabled
            && this.uomDisplayName != this.productUomDisplayName
        );
    }
}
