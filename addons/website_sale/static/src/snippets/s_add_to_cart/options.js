/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

export class AddToCart extends SnippetOption {
    constructor() {
        super(...arguments);
        this.orm = this.env.services.orm;
    }
    /**
     * @override
     */
    async willStart() {
        await super.willStart(...arguments);
        this._updateVariantDomain();
    }

    _setButtonDisabled(isDisabled) {
        const buttonEl = this._buttonEl();

        if (isDisabled) {
            buttonEl.classList.add('disabled');
        } else {
            buttonEl.classList.remove('disabled');
        }
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    async setProductTemplate(previewMode, widgetValue, params) {
        this.$target[0].dataset.productTemplate = widgetValue;
        this._resetVariantChoice();
        this._resetAction();
        this._setButtonDisabled(false);

        await this._fetchVariants(widgetValue);
        this._updateButton();

    }

    setProductVariant(previewMode, widgetValue, params) {
        this.$target[0].dataset.productVariant = widgetValue;
        this._updateButton();
    }

    setAction(previewMode, widgetValue, params) {
        this.$target[0].dataset.action = widgetValue;
        this._updateButton();
    }
    /**
     * @see this.selectClass for parameters
     */
    resetProductPicker(previewMode, widgetValue, params) {
       this._resetProductChoice();
       this._resetVariantChoice();
       this._resetAction();
       this._updateButton();
    }
    /**
     * @see this.selectClass for parameters
     */
    resetVariantPicker(previewMode, widgetValue, params) {
        this._resetVariantChoice();
        this._resetAction();
        this._updateButton();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches the variants ids from the server
     */
    async _fetchVariants(productTemplateId) {
        const response = await this.orm.searchRead(
            "product.product", [["product_tmpl_id", "=", parseInt(productTemplateId)]], ["id"]
        );
        this.$target[0].dataset.variants = response.map(variant => variant.id);
    }


    _resetProductChoice() {
        this.$target[0].dataset.productTemplate = '';
        this._buttonEl().classList.add('disabled');
    }

    _resetVariantChoice() {
        this.$target[0].dataset.productVariant = '';
        this._updateVariantDomain();
    }

    _resetAction() {
        this.$target[0].dataset.action = "add_to_cart";
    }

    /**
     * Returns an array of variant ids from the dom
     */
    _variantIds() {
        return this.$target[0].dataset.variants.split(',').map(stringId => parseInt(stringId));
    }

    _buttonEl() {
        const buttonEl = this.$target[0].querySelector('.s_add_to_cart_btn');
        // In case the button was deleted somehow, we rebuild it.
        if (!buttonEl) {
            return this._buildButtonEl();
        }
        return buttonEl;
    }

    _buildButtonEl() {
        const buttonEl = document.createElement('button');
        buttonEl.classList.add("s_add_to_cart_btn", "btn", "btn-secondary", "mb-2");
        this.$target[0].append(buttonEl);
        return buttonEl;
    }

    /**
     * Updates the button's html
     */
    _updateButton() {
        const variantIds = this._variantIds();
        const buttonEl = this._buttonEl();

        buttonEl.dataset.productTemplateId = this.$target[0].dataset.productTemplate;
        // TODO(loti,vcr): we're aware that getting the product id this way is too simplistic, but
        // it mimics the previous logic. We'll fix this later on.
        buttonEl.dataset.productVariantId =
            variantIds.length > 1 ? this.$target[0].dataset.productVariant : variantIds[0];
        buttonEl.dataset.action = this.$target[0].dataset.action;
        this._updateButtonContent();
    }

    _updateButtonContent() {
        let iconEl = document.createElement('i');
        const buttonContent = {
            add_to_cart: {classList: "fa fa-cart-plus me-2", text: _t("Add to Cart")},
            buy_now: {classList: "fa fa-credit-card me-2", text: _t("Buy now")},
        };
        let buttonContentElement = buttonContent[this.$target[0].dataset.action];

        iconEl.classList = buttonContentElement.classList;

        this._buttonEl().replaceChildren(iconEl, buttonContentElement.text);
    }
    /**
     * @private
     */
    _updateVariantDomain() {
        if (this.$target[0].dataset.productTemplate) {
            // That means that a template was selected and we want to update the
            // content of the variant picker based on the template id.
            this.renderContext.variantDomain = `[["product_tmpl_id", "=", ${this.$target[0].dataset.productTemplate}]]`;
        } else {
            this.renderContext.variantDomain = "[]";
        }
    }

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
        return super._computeWidgetState(...arguments);
    }

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
        return super._computeWidgetVisibility(...arguments);
    }
}
registerWebsiteOption("AddToCart", {
    Class: AddToCart,
    template: "website_sale.s_add_to_cart_options",
    selector: ".s_add_to_cart",
});
