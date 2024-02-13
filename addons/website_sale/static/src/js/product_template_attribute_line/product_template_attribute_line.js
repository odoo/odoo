/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import {
    ProductTemplateAttributeLine
} from '@sale/js/product_template_attribute_line/product_template_attribute_line';

patch(ProductTemplateAttributeLine.prototype, {
    /**
     * Return the product template attribute line, as a read-only display string.
     *
     * @return {String} - The read-only product template attribute line.
     */
    getReadOnlyPtal() {
        const selectedPtavIds = new Set(this.props.selected_attribute_value_ids);
        const selectedPtavNames = this.props.attribute_values
            .filter(ptav => selectedPtavIds.has(ptav.id))
            .map(ptav => ptav.name)
            .join(', ');
        let readOnlyPtalDisplayName = `${this.props.attribute.name}: ${selectedPtavNames}`;
        if (this.isSelectedPTAVCustom()) {
            readOnlyPtalDisplayName += `: ${this.props.customValue}`;
        }
        return readOnlyPtalDisplayName;
    },
});
