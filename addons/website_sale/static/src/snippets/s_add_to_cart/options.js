/** @odoo-module **/

import options from 'web_editor.snippets.options';
import { _t } from 'web.core';

const Many2oneUserValueWidget = options.userValueWidgetsRegistry['we-many2one'];

const Many2oneDefaultMessageWidget = Many2oneUserValueWidget.extend({

    // defaultMessage: default message to display when no records are selected
    configAttributes: [...Many2oneUserValueWidget.prototype.configAttributes, 'defaultMessage'],

    /**
     * @override
     */
    async setValue(value, methodName) {
        await this._super(...arguments);

        if (value === '') {
            this.menuTogglerEl.textContent = this.options.defaultMessage;
        }
    },
});

options.userValueWidgetsRegistry['we-many2one-default-message'] = Many2oneDefaultMessageWidget;

options.registry.AddToCart = options.Class.extend({
    events: _.extend({}, options.Class.prototype.events || {}, {
        'click .reset-variant-picker': '_onClickResetVariantPicker',
        'click .reset-product-picker': '_onClickResetProductPicker',
    }),

    async updateUI() {
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        return this._super.apply(this, arguments);
    },

    _setButtonDisabled: function (isDisabled) {
        const buttonEl = this._buttonEl();

        if (isDisabled) {
            buttonEl.classList.add('disabled');
        } else {
            buttonEl.classList.remove('disabled');
        }
    },

    async setProductTemplate(previewMode, widgetValue, params) {
        this.$target[0].dataset.productTemplate = widgetValue;
        this._resetVariantChoice();
        this._resetAction();
        this._setButtonDisabled(false);

        await this._fetchVariants(widgetValue);
        this.rerender = true;
        this._updateButton();

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
        this._resetAction();
        this._updateButton();
    },

    _onClickResetProductPicker() {
        this._resetProductChoice();
        this._resetVariantChoice();
        this._resetAction();
        this._updateButton();
    },

    /**
     * Fetches the variants ids from the server
     */
    async _fetchVariants(productTemplateId) {
        const response = await this._rpc({
            model: 'product.product',
            method: 'search_read',
            domain: [
                ["product_tmpl_id", "=", parseInt(productTemplateId)],
            ],
            fields: ['id'],
        });
        this.$target[0].dataset.variants = response.map(variant => variant.id);
    },


    _resetProductChoice() {
        this.$target[0].dataset.productTemplate = '';
        this._buttonEl().classList.add('disabled');
    },


    _resetVariantChoice() {
        this.$target[0].dataset.productVariant = '';
    },

    _resetAction: function () {
        this.$target[0].dataset.action = "add_to_cart";
    },

    /**
     * Returns an array of variant ids from the dom
     */
    _variantIds() {
        return this.$target[0].dataset.variants.split(',').map(stringId => parseInt(stringId));
    },

    _buttonEl() {
        const buttonEl = this.$target[0].querySelector('.s_add_to_cart_btn');
        // In case the button was deleted somehow, we rebuild it.
        if (!buttonEl) {
            return this._buildButtonEl();
        }
        return buttonEl;
    },

    _buildButtonEl() {
        const buttonEl = document.createElement('button');
        buttonEl.classList.add("s_add_to_cart_btn", "btn", "btn-secondary", "mb-2");
        this.$target[0].append(buttonEl);
        return buttonEl;
    },

    /**
     * Updates the button's html
     */
    _updateButton() {
        const variantIds = this._variantIds();
        const buttonEl = this._buttonEl();

        let productVariantId = variantIds[0];
        buttonEl.dataset.visitorChoice = false;

        if (variantIds.length > 1) {
            // If there is more than 1 variant, that means that there are variants for the product template
            // and we check if there is one selected and assign it. If not, visitorChoice is set to true
            if (this.$target[0].dataset.productVariant) {
                productVariantId = this.$target[0].dataset.productVariant;
            } else {
                buttonEl.dataset.visitorChoice = true;
            }
        }
        buttonEl.dataset.productVariantId = productVariantId;
        buttonEl.dataset.action = this.$target[0].dataset.action;
        this._updateButtonContent();
        this._createHiddenFormInput(productVariantId);
    },

    _updateButtonContent() {
        let iconEl = document.createElement('i');
        const buttonContent = {
            add_to_cart: {classList: "fa fa-cart-plus me-2", text: _t("Add to Cart")},
            buy_now: {classList: "fa fa-credit-card me-2", text: _t("Buy now")},
        };
        let buttonContentElement = buttonContent[this.$target[0].dataset.action];

        iconEl.classList = buttonContentElement.classList;

        this._buttonEl().replaceChildren(iconEl, buttonContentElement.text);
    },
    /**
     * Because sale_product_configurator._handleAdd() requires a hidden input to retrieve the productId,
     * this method creates a hidden input in the form of the button to make the modal behaviour possible.
     */
    _createHiddenFormInput(productVariantId) {
        const inputEl = this._buttonEl().querySelector('input[type="hidden"][name="product_id"]');
        if (inputEl) {
            // If the input already exists, we change its value
            inputEl.setAttribute('value', productVariantId);
        } else {
            // Otherwise, we create the input element
            let inputEl = document.createElement('input');
            inputEl.setAttribute('type', 'hidden');
            inputEl.setAttribute('name', 'product_id');
            inputEl.setAttribute('value', productVariantId);
            this._buttonEl().append(inputEl);
        }
    },

    /**
     * Called when the template is chosen and that we want to update the m2o variant widget with the right variants.
     */
    async _renderCustomXML(uiFragment) {
        if (this.$target[0].dataset.productTemplate) {
            // That means that a template was selected and we want to update the content of the variant picker based on the template id
            const productVariantPickerEl = uiFragment.querySelector('we-many2one-default-message[data-name="product_variant_picker_opt"]');
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
                return this.$target[0].dataset.productTemplate && this._variantIds().length > 1;
            }
            case 'product_variant_reset_opt': {
                return this.$target[0].dataset.productVariant;
            }

            case 'product_template_reset_opt': {
                return this.$target[0].dataset.productTemplate;
            }
            case 'action_picker_opt': {
                if (this.$target[0].dataset.productTemplate) {
                    if (this._variantIds().length > 1) {
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
