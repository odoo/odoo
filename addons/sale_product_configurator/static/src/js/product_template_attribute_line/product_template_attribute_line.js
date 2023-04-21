/** @odoo-module */

import { Component } from "@odoo/owl";
import { formatMonetary } from "@web/views/fields/formatters";
import { BadgeExtraPrice } from "../badge_extra_price/badge_extra_price";

export class ProductTemplateAttributeLine extends Component {
    static components = { BadgeExtraPrice };
    static template = "saleProductConfigurator.ptal";
    static props = {
        productTmplId: Number,
        id: Number,
        attribute: {
            type: Object,
            shape: {
                id: Number,
                name: String,
                display_type: {
                    type: String,
                    validate: type => ["color", "pills", "radio", "select"].includes(type),
                },
            },
        },
        attribute_values: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    id: Number,
                    name: String,
                    html_color: [Boolean, String], // backend sends 'false' when there is no color
                    is_custom: Boolean,
                    price_extra: Number,
                    excluded: { type: Boolean, optional: true },
                },
            },
        },
        selected_attribute_value_id: Number,
        create_variant: {
            type: String,
            validate: type => ["always", "dynamic", "no_variant"].includes(type),
        },
        customValue: { type: String, optional: true },
    };

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update the selected PTAV in the state.
     *
     * @param {Event} event
     */
    updateSelectedPTAV(event) {
        this.env.updateProductTemplateSelectedPTAV(
            this.props.productTmplId, this.props.id, event.target.value
        );
    }

    /**
     * Update in the state the custom value of the selected PTAV.
     *
     * @param {Event} event
     */
    updateCustomValue(event) {
        this.env.updatePTAVCustomValue(
            this.props.productTmplId, this.props.selected_attribute_value_id, event.target.value
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return template name to use by checking the display type in the props.
     *
     * Each attribute line can have one of this four display types:
     *      - 'Color'  : Display each attribute as a circle filled with said color.
     *      - 'Pills'  : Display each attribute as a rectangle-shaped element.
     *      - 'Radio'  : Display each attribute as a radio element.
     *      - 'Select' : Display each attribute in a selection tag.
     *
     * @return {String} - The template name to use.
     */
    getPTAVTemplate() {
        switch(this.props.attribute.display_type) {
            case 'color':
                return 'saleProductConfigurator.ptav-color';
            case 'pills':
                return 'saleProductConfigurator.ptav-pills';
            case 'radio':
                return 'saleProductConfigurator.ptav-radio';
            case 'select':
                return 'saleProductConfigurator.ptav-select';
        }
    }

    /**
     * Return the name of the PTAV
     *
     * In the selection HTML tag, it is impossible to show the component `BadgeExtraPrice`. Append
     * the extra price to the name to ensure that the extra price will be shown.
     * Note: used in `saleProductConfigurator.ptav-select`.
     *
     * @param {Object} ptav - The attribute, as a `product.template.attribute.value` summary dict.
     * @return {String} - The name of the PTAV.
     */
    getPTAVSelectName(ptav) {
        if (ptav.price_extra) {
            const sign = ptav.price_extra > 0 ? '+' : '-';
            const price = formatMonetary(
                Math.abs(ptav.price_extra),{currencyId: this.env.currencyId}
            );
            return ptav.name +" ("+ sign + " " + price + ")";
        } else {
            return ptav.name;
        }
    }

    /**
     * Check if the selected ptav is custom or not.
     *
     * @return {Boolean} - Whether the selected ptav is custom or not.
     */
    isSelectedPTAVCustom() {
        return this.props.attribute_values.find(
            ptav => this.props.selected_attribute_value_id === ptav.id
        ).is_custom;
    }
 }
