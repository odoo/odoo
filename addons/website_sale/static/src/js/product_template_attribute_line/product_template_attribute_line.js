/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import {
    ProductTemplateAttributeLine
} from '@sale/js/product_template_attribute_line/product_template_attribute_line';

patch(ProductTemplateAttributeLine.prototype, {
    /**
     * Return the display name of this PTAL.
     *
     * @return {String} - The display name of this PTAL.
     */
    getPtalDisplayName() {
        const selectedPtavIds = new Set(this.props.selected_attribute_value_ids);
        const selectedPtavNames = this.props.attribute_values
            .filter(ptav => selectedPtavIds.has(ptav.id))
            .map(ptav => ptav.name)
            .join(', ');
        let ptalDisplayName = `${this.props.attribute.name}: ${selectedPtavNames}`;
        if (this.isSelectedPTAVCustom()) {
            ptalDisplayName += `: ${this.props.customValue}`;
        }
        return ptalDisplayName;
    },
});
