import { _t } from '@web/core/l10n/translation';
import {
    ProductTemplateAttributeLine
} from '@sale/js/product_template_attribute_line/product_template_attribute_line';
import { patch } from '@web/core/utils/patch';

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

    get customValuePlaceholder() {
        // The original definition of this placeholder is in `sale` module which is not a frontend module. However, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Enter a customized value");
    },
});
