/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';
import { _t } from "@web/core/l10n/translation";

options.registry.RentalSearchOptions = options.Class.extend({
    events: Object.assign({}, options.Class.prototype.events || {}, {
        'click .reset-product-attribute-picker': '_onClickResetProductAttributePicker',
    }),

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    start() {
        this._super.apply(this, arguments);
        if (!this.$target[0].dataset.timing) {
            this.$target[0].dataset.timing = 'day';
        }
    },

    /**
     * This function set the visibility of the select widget
     * @param visible
     * @private
     */
    _setProductAttributeSelectVisibility(visible) {
        const productAttributeSearchRentalEl = this.$target[0].querySelector('.product_attribute_search_rental');
        if (visible) {
            productAttributeSearchRentalEl.classList.remove('d-none');
        } else {
            productAttributeSearchRentalEl.classList.add('d-none');
        }
    },
    /**
     * This function set the content of the select widget.
     * @param widgetValue
     * @private
     */
    _setProductAttributeSelect(widgetValue) {
        const productAttributeNameEl = this.$target[0].querySelector('.product_attribute_search_rental_name');
        productAttributeNameEl.id = widgetValue;
    },

    async setProductAttribute(previewMode, widgetValue, params) {
        this.$target[0].dataset.productAttribute = widgetValue;
        this._setProductAttributeSelectVisibility(true);
        this._setProductAttributeSelect(widgetValue);
        await this._populateProductAttributeSelect(widgetValue);
    },
    /**
     * This function set the timing of the snippet.
     * @param previewMode
     * @param widgetValue
     * @param params
     */
    setTiming(previewMode, widgetValue, params) {
        this.$target[0].dataset.timing = widgetValue;

        const timingHiddenInput = this.$target[0].querySelector('.s_rental_search_rental_duration_unit');
        timingHiddenInput.value = widgetValue;
    },

    /**
     * This function is triggered when the user clicks on the reset button.
     * @private
     */
    _onClickResetProductAttributePicker() {
        this.$target[0].dataset.productAttribute = '';
        this._setProductAttributeSelectVisibility(false);
        this._setProductAttributeSelect('');
    },

    /**
     *
     * @param methodName
     * @param params
     * @returns {string|string|*}
     * @private
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'setProductAttribute': {
                return this.$target[0].dataset.productAttribute || '';
            }
            case 'setTiming': {
                return this.$target[0].dataset.timing;
            }
        }
        return this._super(...arguments);
    },

    /**
     *
     * @param widgetName
     * @param params
     * @returns {Promise<string|*>}
     * @private
     */
    async _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case 'product_attribute_reset_opt': {
                return this.$target[0].dataset.productAttribute;
            }
            case 'timing_picker_opt': {
                return this.$target[0].dataset.timing;
            }
        }
        return this._super(...arguments);
    },

    /**
     * This function populate the select widget with the product attributes
     * @param widgetValue
     * @returns {Promise<void>}
     * @private
     */
    async _populateProductAttributeSelect(widgetValue) {
        const response = await this.orm.searchRead(
            "product.attribute.value",
            [["attribute_id", "=", parseInt(widgetValue)]],
            []
        );
        const productAttributeSelectEl = this.$target[0].querySelector('.s_rental_search_select');
        productAttributeSelectEl.replaceChildren();
        productAttributeSelectEl.appendChild(this._addOptionToSelect({id: '', name: _t("All")}));
        for (const record of response) {
            productAttributeSelectEl.appendChild(this._addOptionToSelect(record));
        }
    },

    /**
     * This function add an option to the select widget
     * @param record
     */
    _addOptionToSelect(record) {
        const optionEl = document.createElement('option');
        optionEl.value = record.id;
        optionEl.innerText = record.name;
        return optionEl;
    },
});

export default {
    RentalSearchOptions: options.registry.RentalSearchOptions,
};
