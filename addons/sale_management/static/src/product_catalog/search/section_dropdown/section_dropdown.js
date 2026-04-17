import { SectionDropdown } from "@account/components/product_catalog/search/section_dropdown/section_dropdown";
import { patch } from '@web/core/utils/patch';

patch(SectionDropdown.prototype, {

    _getToggleFieldsOfSection() {
        return [...super._getToggleFieldsOfSection(), "is_optional"];
    },

    disableCompositionButton() {
        return !!(
            super.disableCompositionButton()
            || this.parent?.is_optional
            || this.props.section.is_optional
        );
    },

    disableOptionalButton() {
        return !!(
            this.parent?.is_optional
            || this.parent?.collapse_prices
            || this.parent?.collapse_composition
        );
    },

    disablePricesButton() {
        return !!(
            super.disablePricesButton()
            || this.parent?.is_optional
            || this.props.section.is_optional
        );
    }
})
