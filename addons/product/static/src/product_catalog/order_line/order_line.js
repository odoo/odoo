import { onWillRender } from "@web/owl2/utils";
import { Component, onMounted, Portal, signal, t, useProps } from "@odoo/owl";
import { formatFloat, formatMonetary } from "@web/views/fields/formatters";

export class ProductCatalogOrderLine extends Component {
    static template = "product.ProductCatalogOrderLine";
    static components = { Portal };

    props = useProps({
        isSample: t.boolean().optional(),
        productId: t.number(),
        quantity: t.number(),
        readOnly: t.boolean().optional(),
        warning: t.string().optional(),

        // price data
        price: t.number().optional(),
        subtotal: t.number().optional(),

        // UoM data, if uoms are enabled
        uomId: t.number().optional(),
        productUomId: t.number().optional(),
        availableUoms: t.array(t.object()).optional(),
    });

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
        const productUnitPrice = this.props.price * (this.productUom.factor / this.uom.factor || 1);
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
        return this.isUoMFeatureEnabled && this.props.availableUoms.length > 1;
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

    get uomSelectStyle() {
        const name = this.uomDisplayName || "";
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
            && this.props.uomId != this.props.productUomId
        );
    }
}
