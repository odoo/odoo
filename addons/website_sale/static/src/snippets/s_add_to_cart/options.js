/** @odoo-module **/

import options from 'web_editor.snippets.options';
import {_t} from 'web.core';

options.registry.AddToCart = options.Class.extend({
    events: _.extend({}, options.Class.prototype.events || {}, {
        'click .reset-variant-picker': '_onClickResetVariantPicker',
    }),

    async updateUI() {
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        return this._super.apply(this, arguments);
    },

    async setProductTemplate(previewMode, widgetValue, params) {
        this.$target[0].dataset.productTemplate = widgetValue;
        this._resetVariantChoice();
        // We retrieve the variants to compute wether we display or not the variant picker.
        await this._fetchVariants(widgetValue);
        this.rerender = true;
        this.$target[0].dataset.action = "add_to_cart";
        this._updateButton()
    },

    setProductVariant(previewMode, widgetValue, params) {
        this.$target[0].dataset.productVariant = widgetValue;
        this._updateButton();
    },

    setAction(previewMode, widgetValue, params) {
        this.$target[0].dataset.action = widgetValue;
        this._updateButton();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onClickResetVariantPicker() {
        this._resetVariantChoice();
        this._updateButton()
    },

    /**
     * Fetches the variants ids from the server
     */
    async _fetchVariants(productTemplateId) {
        const self = this;
        const response = await this._rpc({
            model: 'product.product',
            method: 'search_read',
            domain: [["product_tmpl_id", "=", parseInt(productTemplateId)]],

        });
        self.$target[0].dataset.variants = response.map(variant => variant.id);
    },


    _resetVariantChoice() {
        this.$target[0].dataset.productVariant = '';
    },

    /**
     * Returns an array of variant ids from the dom
     */
    _variants() {
        if (!this.$target[0].dataset.variants) return;

        return this.$target[0].dataset.variants.split(',').map(stringId => parseInt(stringId))
    },

    /**
     * Updates the button's html
     */
    _updateButton() {
        const buttonEl = this.$target[0].querySelector('#s_add_to_cart_button');
        const variants = this._variants();
        let productVariantId;

        buttonEl.dataset.visitorChoice = "";
        if (variants.length === 1) {
            productVariantId = variants[0];
        } else {
            if (!this.$target[0].dataset.productVariant) {
                productVariantId = variants[0];
                buttonEl.dataset.visitorChoice = "true";
            } else {
                productVariantId = this.$target[0].dataset.productVariant;

            }
        }
        buttonEl.dataset.productVariant = productVariantId;
        buttonEl.dataset.action = this.$target[0].dataset.action;
        this._updateButtonText(this.$target[0].dataset.action);
        this._createHiddenFormInput(productVariantId);
    },

    _updateButtonText(action) {
        const buttonTextEl = this.$target[0].querySelector('#s_add_to_cart_button_text');
        const textContents = {
            add_to_cart: _t("Add to Cart"),
            buy_now: _t("Buy Now"),
        };
        buttonTextEl.textContent = textContents[action];
    },
    /**
     * Because sale_product_configurator._handleAdd() requires a hidden input to retrieve the productId,
     * this method creates a hidden input in the form of the button to make the modal behaviour possible.
     */
    _createHiddenFormInput(productVariantId) {
        const $form = this.$target.children('form');
        const $input = $form.find('input[type="hidden"][name="product_id"]');

        if ($input.length) {
            // If the input already exists, we change its value
            $input.attr('value', productVariantId);
        } else {
            // Otherwise, we create the input element
            let inputEl = document.createElement('input');
            inputEl.setAttribute('type', 'hidden');
            inputEl.setAttribute('name', 'product_id');
            inputEl.setAttribute('value', productVariantId);
            $form.append(inputEl);
        }
    },

    /**
     * Called when the template is chosen and that we want to update the m2o variant widget with the right variants.
     */
    async _renderCustomXML(uiFragment) {
        if (this.$target[0].dataset.productTemplate) {
            // That means that a template was selected and we want to update the content of the variant picker based on the template id
            const productVariantPickerEl = uiFragment.querySelector('we-many2one[data-name="product_variant_picker_opt"]');
            productVariantPickerEl.dataset.domain = `[["product_tmpl_id", "=", ${this.$target[0].dataset.productTemplate}]]`;
        }
    },

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'setProductTemplate': {
                return this.$target[0].dataset.productTemplate || '';
            }
            case 'setProductVariant': {
                return this.$target[0].dataset.productVariant || '';
            }
            case 'setAction': {
                return this.$target[0].dataset.action;
            }
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case 'product_variant_picker_opt': {
                return this.$target[0].dataset.productTemplate && this._variants().length > 1;
            }
            case 'product_variant_reset_opt': {
                return this.$target[0].dataset.productVariant;
            }
            case 'action_picker_opt': {
                if (this.$target[0].dataset.productTemplate){
                    if (this._variants().length > 1){
                        return this.$target[0].dataset.productVariant;
                    }
                    return true;
                }
                return false;
            }
        }
        return this._super(...arguments);
    },
});
export default {
    AddToCart: options.registry.AddToCart,
};
