import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { BadgeExtraPrice } from "../badge_extra_price/badge_extra_price";
import { getSelectedCustomPtav } from "../sale_utils";

export class ProductTemplateAttributeLine extends Component {
    static components = { BadgeExtraPrice };
    static template = "sale.ProductTemplateAttributeLine";
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
                    validate: type => ["color", "multi", "pills", "radio", "select", "image"].includes(type),
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
                    image: [Boolean, String], // backend sends 'false' when there is no image set
                    is_custom: Boolean,
                    price_extra: Number,
                    excluded: { type: Boolean, optional: true },
                },
            },
        },
        selected_attribute_value_ids: { type: Array, element: Number },
        create_variant: {
            type: String,
            validate: type => ["always", "dynamic", "no_variant"].includes(type),
        },
        customValue: {type: [{value: false}, String], optional: true},
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
            this.props.productTmplId, this.props.id, event.target.value, this.props.attribute.display_type == 'multi'
        );
    }

    /**
     * Update in the state the custom value of the selected PTAV.
     *
     * @param {Event} event
     */
    updateCustomValue(event) {
        this.env.updatePTAVCustomValue(
            this.props.productTmplId, this.props.selected_attribute_value_ids[0], event.target.value
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return template name to use by checking the display type in the props.
     *
     * Each attribute line can have one of this five display types:
     *      - 'Color'  : Display each attribute as a circle filled with said color.
     *      - 'Pills'  : Display each attribute as a rectangle-shaped element.
     *      - 'Radio'  : Display each attribute as a radio element.
     *      - 'Select' : Display each attribute in a selection tag.
     *      - 'Multi'  : Display each attribute in a multi-checkbox tag.
     *
     * @return {String} - The template name to use.
     */
    getPTAVTemplate() {
        switch(this.props.attribute.display_type) {
            case 'select':
                return 'sale.ptav_select';
            case 'radio':
                return 'sale.ptav_radio';
            case 'pills':
                return 'sale.ptav_pills';
            case 'color':
                return 'sale.ptav_color';
            case 'multi':
                return 'sale.ptav_multi';
            case 'image':
                return 'sale.ptav_image';
        }
    }

    /**
     * Return the name of the PTAV
     *
     * In the selection HTML tag, it is impossible to show the component `BadgeExtraPrice`. Append
     * the extra price to the name to ensure that the extra price will be shown.
     * Note: used in `sale.ptav_select`.
     *
     * @param {Object} ptav - The attribute, as a `product.template.attribute.value` summary dict.
     * @return {String} - The name of the PTAV.
     */
    getPTAVSelectName(ptav) {
        if (ptav.price_extra) {
            const sign = ptav.price_extra > 0 ? '+' : '-';
            const price = formatCurrency(Math.abs(ptav.price_extra), this.env.currency.id);
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
        return !!getSelectedCustomPtav(this.props);
    }

    get showValuesChoice() {
        return (this.env.canChangeVariant || this.props.create_variant === 'no_variant') && (
            this.props.attribute_values.length > 1 || this.props.attribute.display_type === 'multi'
        )
    }

    get customValuePlaceholder() {
        return _t("Enter a customized value");
    }

    /**
     * Check if the line has a custom ptav or not.
     *
     * @return {Boolean} - Whether the line has a custom ptav or not.
     */
    hasPTAVCustom() {
        return this.props.attribute_values.some(
            ptav => ptav.is_custom
        );
    }
 }
