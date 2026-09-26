
import { Component, t, useProps } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import {
    ProductTemplateAttributeLine as PTAL
} from "../product_template_attribute_line/product_template_attribute_line";
import { QuantityButtons } from '../quantity_buttons/quantity_buttons';
import { getSelectedCustomPtav } from "../sale_utils";
import { _t } from "@web/core/l10n/translation";

// Exported so overriding modules can extend the schema (props is now an instance
// field, so `Product.props` no longer resolves; they must augment this instead).
export const productProps = {
    id: t.or([t.number(), t.literal(false)]).optional(),
    product_tmpl_id: t.number(),
    display_name: t.string(),
    // backend sends 'false' when there is no description
    description_sale: t.or([t.boolean(), t.string()]),
    price: t.number(),
    quantity: t.number(),
    uom: t.object().optional(),
    available_uoms: t.array().optional(),
    attribute_lines: t.array(),
    optional: t.boolean(),
    imageURL: t.string().optional(),
    archived_combinations: t.array(),
    exclusions: t.object(),
    parent_product_tmpl_id: t.number().optional(),
    price_info: t.string().optional(),
    selectedComboItems: t.array(t.object({ name: t.string() })).optional(),
};

export class Product extends Component {
    static components = { PTAL, QuantityButtons };
    static template = "sale.Product";
    props = useProps(productProps);

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the price, in the format of the given currency.
     *
     * @return {String} - The price, in the format of the given currency.
     */
    getFormattedPrice(price) {
        return formatCurrency(price, this.env.currencyId);
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
