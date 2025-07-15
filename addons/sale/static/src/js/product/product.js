
import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import {
    ProductTemplateAttributeLine as PTAL
} from "../product_template_attribute_line/product_template_attribute_line";
import { QuantityButtons } from '../quantity_buttons/quantity_buttons';
import { getSelectedCustomPtav } from "../sale_utils";
import { _t } from "@web/core/l10n/translation";

export class Product extends Component {
    static components = { PTAL, QuantityButtons };
    static template = "sale.Product";
    static props = {
        id: { type: [Number, {value: false}], optional: true },
        product_tmpl_id: Number,
        display_name: String,
        description_sale: [Boolean, String], // backend sends 'false' when there is no description
        price: Number,
        quantity: Number,
        uom: { type: Object, optional: true },
        available_uoms: { type: Object, optional: true },
        attribute_lines: Object,
        optional: Boolean,
        imageURL: { type: String, optional: true },
        archived_combinations: Array,
        exclusions: Object,
        parent_exclusions: Object,
        parent_product_tmpl_id: { type: Number, optional: true },
        price_info: { type: String, optional: true },
        selectedComboItems: {
            type: Array,
            element: Object,
            shape: {
                name: String,
            },
            optional: true,
        },
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
        return formatCurrency(this.props.price, this.env.currency.id);
    }

    /**
     * Check whether this product is the main product.
     *
     * @return {Boolean} - Whether this product is the main product.
     */
    get isMainProduct() {
        return this.env.mainProductTmplId === this.props.product_tmpl_id;
    }

    /**
     * Return this product's image URL.
     *
     * @return {String} This product's image URL.
     */
    get imageUrl() {
        const modelPath = this.props.id
            ? `product.product/${ this.props.id }`
            : `product.template/${ this.props.product_tmpl_id }`;
        return `/web/image/${ modelPath }/image_256`;
    }

    /**
     * Check whether the provided PTAL should be shown.
     *
     * @return {Boolean} Whether the PTAL should be shown.
     */
    shouldShowPtal(ptal) {
        return this.env.canChangeVariant
            || ptal.create_variant === 'no_variant'
            || !!getSelectedCustomPtav(ptal);
    }


    get UoMTitle() {
        return _t("Packaging");
    }

    async selectUoM(event) {
        this.env.setUoM(this.props.product_tmpl_id, parseInt(event.target.value));
    }

}
