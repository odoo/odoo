import { _t } from '@web/core/l10n/translation';
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

    get customValuePlaceholder() {
        // The original definition of this placeholder is in `sale` module which is not a frontend module. However, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Enter a customized value");
    },
});
