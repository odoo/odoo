/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { formatCurrency } from "@web/core/currency";
import { BadgeExtraPrice } from "@sale_product_configurator/js/badge_extra_price/badge_extra_price";
import { ProductTemplateAttributeLine } from "@product/js/product_configurator/product_template_attribute_line/product_template_attribute_line"


ProductTemplateAttributeLine.components = { BadgeExtraPrice };

ProductTemplateAttributeLine.props = {
    ...ProductTemplateAttributeLine.props,
    attribute_values: {
        type: Array,
        element: {
            type: Object,
            shape: {
                id: Number,
                name: String,
                html_color: [String, { value: false }],
                image: [Boolean, String], // backend sends 'false' when there is no image set
                is_custom: Boolean,
                price_extra: { type: Number, optional: true },
                excluded: { type: Boolean, optional: true },
            },
        },
    },
};

patch(ProductTemplateAttributeLine.prototype, {
    /**
     * Override of `product` to show the optional extra price in the option's display name.
     *
     * In the selection HTML tag, it is impossible to show the component `BadgeExtraPrice`. Append
     * the extra price to the name to ensure that the extra price will be shown.
     *
     * @param {Object} ptav - The attribute, as a `product.template.attribute.value` summary dict.
     * @return {String} - The name of the PTAV.
     * */
    getPTAVSelectName(ptav) {
        if (ptav.price_extra) {
            const sign = ptav.price_extra > 0 ? '+' : '-';
            const price = formatCurrency(
                Math.abs(ptav.price_extra), this.env.currencyId
            );
            return ptav.name +" ("+ sign + " " + price + ")";
        } else {
            return super.getPTAVSelectName(ptav);
        }
    },
 })
